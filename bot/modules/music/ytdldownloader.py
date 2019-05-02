import os
import asyncio
import functools
import youtube_dl
from ...playback import Entry
from ...utils import get_header, md5sum

from concurrent.futures import ThreadPoolExecutor

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'usenetrc': True
}

youtube_dl.utils.bug_reports_message = lambda: ''

'''
    Alright, here's the problem.  To catch youtube-dl errors for their useful information, I have to
    catch the exceptions with `ignoreerrors` off.  To not break when ytdl hits a dumb video
    (rental videos, etc), I have to have `ignoreerrors` on.  I can change these whenever, but with async
    that's bad.  So I need multiple ytdl objects.

'''

class YtdlDownloader:
    def __init__(self, bot, download_folder=None):
        self._bot = bot
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        self.unsafe_ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        self.safe_ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
        self.safe_ytdl.params['ignoreerrors'] = True
        os.makedirs(os.path.dirname('/data/{}/'.format(download_folder)), exist_ok=True)
        self.download_folder = '/data/{}'.format(download_folder)

        if self.download_folder:
            otmpl = self.unsafe_ytdl.params['outtmpl']
            self.unsafe_ytdl.params['outtmpl'] = os.path.join(self.download_folder, otmpl)
            # print("setting template to " + os.path.join(self.download_folder, otmpl))

            otmpl = self.safe_ytdl.params['outtmpl']
            self.safe_ytdl.params['outtmpl'] = os.path.join(self.download_folder, otmpl)

    def shutdown(self):
        self.thread_pool.shutdown()

    @property
    def ytdl(self):
        return self.safe_ytdl

    async def extract_info(self, *args, on_error=None, retry_on_error=False, **kwargs):
        """
            Runs ytdl.extract_info within the threadpool. Returns a future that will fire when it's done.
            If `on_error` is passed and an exception is raised, the exception will be caught and passed to
            on_error as an argument.
        """
        if callable(on_error):
            try:
                return await self._bot.loop.run_in_executor(self.thread_pool, functools.partial(self.unsafe_ytdl.extract_info, *args, **kwargs))

            except Exception as e:

                # (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError)
                # I hope I don't have to deal with ContentTooShortError's
                if asyncio.iscoroutinefunction(on_error):
                    asyncio.ensure_future(on_error(e), loop=self._bot.loop)

                elif asyncio.iscoroutine(on_error):
                    asyncio.ensure_future(on_error, loop=self._bot.loop)

                else:
                    self._bot.loop.call_soon_threadsafe(on_error, e)

                if retry_on_error:
                    return await self.safe_extract_info(self._bot.loop, *args, **kwargs)
        else:
            return await self._bot.loop.run_in_executor(self.thread_pool, functools.partial(self.unsafe_ytdl.extract_info, *args, **kwargs))

    async def safe_extract_info(self, *args, **kwargs):
        return await self._bot.loop.run_in_executor(self.thread_pool, functools.partial(self.safe_ytdl.extract_info, *args, **kwargs))

    async def process_url_to_info(self, song_url, on_search_error = None):
        while True:
            try:
                info = await self.extract_info(song_url, download=False, process=False)
                # If there is an exception arise when processing we go on and let extract_info down the line report it
                # because info might be a playlist and thing that's broke it might be individual entry
                try:
                    info_process = await self.extract_info(song_url, download=False)
                except:
                    info_process = None
                    
                self._bot.log.debug(info)
                if info_process and info and info_process.get('_type', None) == 'playlist' and 'entries' not in info and not info.get('url', '').startswith('ytsearch'):
                    use_url = info_process.get('webpage_url', None) or info_process.get('url', None)
                    if use_url == song_url:
                        self._bot.log.warning("Determined incorrect entry type, but suggested url is the same.  Help.")
                        break # If we break here it will break things down the line and give "This is a playlist" exception as a result

                    self._bot.log.debug("Assumed url \"%s\" was a single entry, was actually a playlist" % song_url)
                    self._bot.log.debug("Using \"%s\" instead" % use_url)
                    song_url = use_url
                else:
                    break

            except Exception as e:
                if 'unknown url type' in str(e):
                    song_url = song_url.replace(':', '')  # it's probably not actually an extractor
                    info = await self.extract_info(song_url, download=False, process=False)
                else:
                    raise e

        if not info:
            raise Exception("That video cannot be played. Try using the stream command.")

        # abstract the search handling away from the user
        # our ytdl options allow us to use search strings as input urls
        if info.get('url', '').startswith('ytsearch'):
            info = await self.extract_info(
                song_url,
                download=False,
                process=True,    # ASYNC LAMBDAS WHEN
                on_error=on_search_error,
                retry_on_error=True
            )

            if not info:
                raise Exception(
                    "Error extracting info from search string, youtubedl returned no data. "
                    "You may need to restart the bot if this continues to happen."
                )

            if not all(info.get('entries', [])):
                # empty list, no data
                self._bot.log.debug("Got empty list, no data")
                return

            # TODO: handle 'webpage_url' being 'ytsearch:...' or extractor type
            song_url = info['entries'][0]['webpage_url']
            info = await self.extract_info(song_url, download=False, process=False)

        return (info, song_url)

class YtdlUrlEntry(Entry):
    def __init__(self, url, title, duration, metadata, extractor, expected_filename=None):
        self._extractor = extractor
        super().__init__(url, title, duration, metadata)
        self._download_folder = self._extractor.download_folder
        self._expected_filename = expected_filename

    async def prepare_cache(self):
        async with self._aiolocks['preparing_cache_set']:
            if self._preparing_cache:
                return
            self._preparing_cache = True

        extractor = os.path.basename(self._expected_filename).split('-')[0]

        # the generic extractor requires special handling
        if extractor == 'generic':
            flistdir = [f.rsplit('-', 1)[0] for f in os.listdir(self._download_folder)]
            expected_fname_noex, fname_ex = os.path.basename(self._expected_filename).rsplit('.', 1)

            if expected_fname_noex in flistdir:
                try:
                    rsize = int(await get_header(self._extractor._bot.aiosession, self.source_url, 'CONTENT-LENGTH'))
                except:
                    rsize = 0

                lfile = os.path.join(
                    self._download_folder,
                    os.listdir(self._download_folder)[flistdir.index(expected_fname_noex)]
                )

                # print("Resolved %s to %s" % (self.expected_filename, lfile))
                lsize = os.path.getsize(lfile)
                # print("Remote size: %s Local size: %s" % (rsize, lsize))

                if lsize != rsize:
                    await self._really_download(hashing=True)
                else:
                    # print("[Download] Cached:", self.url)
                    self._local_url = lfile

            else:
                # print("File not found in cache (%s)" % expected_fname_noex)
                await self._really_download(hashing=True)

        else:
            ldir = os.listdir(self._download_folder)
            flistdir = [f.rsplit('.', 1)[0] for f in ldir]
            expected_fname_base = os.path.basename(self._expected_filename)
            expected_fname_noex = expected_fname_base.rsplit('.', 1)[0]

            # idk wtf this is but its probably legacy code
            # or i have youtube to blame for changing shit again

            if expected_fname_base in ldir:
                self._local_url = os.path.join(self._download_folder, expected_fname_base)
                self._extractor._bot.log.info("Download cached: {}".format(self.source_url))

            elif expected_fname_noex in flistdir:
                self._extractor._bot.log.info("Download cached (different extension): {}".format(self.source_url))
                self._local_url = os.path.join(self._download_folder, ldir[flistdir.index(expected_fname_noex)])
                self._extractor._bot.log.debug("Expected {}, got {}".format(
                    self._expected_filename.rsplit('.', 1)[-1],
                    self._local_url.rsplit('.', 1)[-1]
                ))
            else:
                await self._really_download()

        # TODO: equalization

        async with self._aiolocks['preparing_cache_set']:
            async with self._aiolocks['cached_set']:
                self._preparing_cache = False
                self._cached = True

    async def _really_download(self, *, hashing=False):
        self._extractor._bot.log.info("Download started: {}".format(self.source_url))

        retry = True
        while retry:
            try:
                result = await self._extractor.extract_info(self.source_url, download=True)
                break
            except Exception as e:
                raise e

        self._extractor._bot.log.info("Download complete: {}".format(self.source_url))

        if result is None:
            self._extractor._bot.log.critical("YTDL has failed, everyone panic")
            raise Exception("ytdl broke and hell if I know why")
            # What the fuck do I do now?

        self._local_url = unhashed_fname = self._extractor.ytdl.prepare_filename(result)


        # TODO: check storage limit


        if hashing:
            # insert the 8 last characters of the file hash to the file name to ensure uniqueness
            self._local_url = md5sum(unhashed_fname, 8).join('-.').join(unhashed_fname.rsplit('.', 1))

            if os.path.isfile(self._local_url):
                # Oh bother it was actually there.
                os.unlink(unhashed_fname)
            else:
                # Move the temporary file to it's final location.
                os.rename(unhashed_fname, self._local_url)

class WrongEntryTypeError(Exception):
    def __init__(self, message, is_playlist, use_url):
        super().__init__(message)
        self.is_playlist = is_playlist
        self.use_url = use_url

async def get_entry(song_url, extractor, metadata):
    try:
        info = await extractor.extract_info(extractor._bot.loop, song_url, download=False)
    except Exception as e:
        raise Exception('Could not extract information from {}\n\n{}'.format(song_url, e))

    if not info:
        raise Exception('Could not extract information from %s' % song_url)

    # TODO: Sort out what happens next when this happens
    if info.get('_type', None) == 'playlist':
        raise WrongEntryTypeError("This is a playlist.", True, info.get('webpage_url', None) or info.get('url', None))

    if info.get('is_live', False):
        # TODO: return stream entry
        pass

    # TODO: Extract this to its own function
    if info['extractor'] in ['generic', 'Dropbox']:
        extractor._bot.log.debug('Detected a generic extractor, or Dropbox')
        try:
            headers = await get_header(extractor._bot.aiosession, info['url'])
            content_type = headers.get('CONTENT-TYPE')
            extractor._bot.log.debug("Got content type {}".format(content_type))
        except Exception as e:
            extractor._bot.log.warning("Failed to get content type for url {} ({})".format(song_url, e))
            content_type = None

        if content_type:
            if content_type.startswith(('application/', 'image/')):
                if not any(x in content_type for x in ('/ogg', '/octet-stream')):
                    # How does a server say `application/ogg` what the actual fuck
                    raise Exception("Invalid content type \"%s\" for url %s" % (content_type, song_url))

            elif content_type.startswith('text/html') and info['extractor'] == 'generic':
                extractor._bot.log.warning("Got text/html for content-type, this might be a stream.")
                # TODO: return stream entry
                pass

            elif not content_type.startswith(('audio/', 'video/')):
                extractor._bot.log.warning("Questionable content-type \"{}\" for url {}".format(content_type, song_url))

    entry = YtdlUrlEntry(
        song_url,
        info.get('title', 'Untitled'),
        info.get('duration', 0) or 0,
        metadata,
        extractor,
        extractor.ytdl.prepare_filename(info)
    )

    return entry

async def get_entry_list_from_playlist_url(playlist_url, extractor, metadata):
    entry_list = []

    try:
        info = await extractor.safe_extract_info(playlist_url, download=False)
    except Exception as e:
        raise Exception('Could not extract information from {}\n\n{}'.format(playlist_url, e))

    if not info:
        raise Exception('Could not extract information from %s' % playlist_url)

    # Once again, the generic extractor fucks things up.
    if info.get('extractor', None) == 'generic':
        url_field = 'url'
    else:
        url_field = 'webpage_url'

    baditems = 0
    for item in info['entries']:
        if item:
            try:
                entry = YtdlUrlEntry(
                    item[url_field],
                    item.get('title', 'Untitled'),
                    item.get('duration', 0) or 0,
                    metadata,
                    extractor,
                    extractor.ytdl.prepare_filename(info)
                )
                entry_list.append(entry)
            except Exception as e:
                baditems += 1
                extractor._bot.log.warning("Could not add item", exc_info=e)
                extractor._bot.log.debug("Item: {}".format(item), exc_info=True)
        else:
            baditems += 1

    if baditems:
        extractor._bot.log.info("Skipped {} bad entries".format(baditems))

    return entry_list