import asyncio
import logging
import sys
from bot import logger
from bot.bot import ModuBot
from bot.config import Config, ConfigDefaults
import threading
import time
from platform import system

if __name__ == "__main__":
    import colorlog
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setFormatter(colorlog.LevelFormatter(
        fmt = {
            'DEBUG': '{log_color}[{levelname}:{module}:{name}] {message}',
            'INFO': '{log_color}[{levelname}:{module}:{name}] {message}',
            'WARNING': '{log_color}[{levelname}:{module}:{name}] {message}',
            'ERROR': '{log_color}[{levelname}:{module}:{name}] {message}',
            'CRITICAL': '{log_color}[{levelname}:{module}:{name}] {message}',

            'EVERYTHING': '{log_color}[{levelname}:{module}:{name}] {message}',
            'NOISY': '{log_color}[{levelname}:{module}:{name}] {message}'
        },
        log_colors = {
            'DEBUG':    'cyan',
            'INFO':     'white',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'bold_red',

            'EVERYTHING': 'white',
            'NOISY':      'white'
        },
            style = '{'
    ))
    log.addHandler(sh)
    logger.addHandler(sh)

    logfile = open('logs/log.txt','w', encoding='utf-8')

    fh = logging.StreamHandler(stream=logfile)
    fh.setFormatter(logging.Formatter(
        fmt="[%(relativeCreated).9f] %(asctime)s - %(levelname)s - %(name)s: %(message)s"
    ))
    log.addHandler(fh)
    logger.addHandler(fh)

    loop = asyncio.get_event_loop()

    config = Config(ConfigDefaults.config_file)
    bot = ModuBot(loop=loop, conf=config, loghandlerlist=[sh, fh], max_messages=10000)
    loop.run_until_complete(bot.load_modules(['default', 'permission', 'announce', 'music']))

    shutdown = False
    safe_shutdown = threading.Lock()
    spawned_thread_safe_exit = threading.Lock()

    thread = False

    def logouthandler(sig, stackframe=None):
        global thread
        if system() == 'Windows':
            thread = True
        log.debug('\nAcquiring ... (logouthandler/{})'.format(system()))
        safe_shutdown.acquire()
        global shutdown
        if not shutdown:            
            shutdown = True
            log.info('\nShutting down ... (logouthandler/{})'.format(system()))
            log.info(sig)
            bot.logout()
        log.debug('\nReleasing ... (logouthandler/{})'.format(system()))
        safe_shutdown.release()
        log.debug('\nAcquiring safe ... (logouthandler/{})'.format(system()))
        spawned_thread_safe_exit.acquire() # This help main thread to not get KeyboardInterrupt while doing work
        log.debug('\nReleasing safe ... (logouthandler/{})'.format(system()))
        spawned_thread_safe_exit.release() # At least for pywin32

    abortKeyboardInterrupt = False
    
    if system() == 'Windows':
        try:
            from win32.win32api import SetConsoleCtrlHandler
            SetConsoleCtrlHandler(logouthandler, True)
            abortKeyboardInterrupt = True
        except ImportError:
            version = '.'.join(map(str, sys.version_info))
            log.warning('pywin32 not installed for Python {}. Please stop the bot using KeyboardInterrupt instead of the close button.'.format(version))
    
    else:
        import atexit
        atexit.register(logouthandler, 0)
    
    try:
        bot.run()
        log.debug('\nAcquiring safe ...')
        spawned_thread_safe_exit.acquire()
        log.debug('\nAcquiring ... (RunExit)')
        safe_shutdown.acquire()
        if not shutdown:            
            shutdown = True
            log.info('\nShutting down ... (RunExit)')
            bot.logout()
        log.debug('\nReleasing ... (RunExit)')
        safe_shutdown.release()
    except KeyboardInterrupt:
        if not abortKeyboardInterrupt:
            log.debug('\nAcquiring ... (KeyboardInterrupt)')
            safe_shutdown.acquire()
            if not shutdown:
                shutdown = True
                log.info('\nShutting down ... (KeyboardInterrupt)')
                bot.logout()
            log.debug('\nReleasing ... (KeyboardInterrupt)')
            safe_shutdown.release()
    except RuntimeError:
        log.debug('\nAcquiring ... (RuntimeError)')
        safe_shutdown.acquire()
        if not shutdown:
            shutdown = True
            log.info('\nShutting down ... (RuntimeError)')
            bot.logout()
        log.debug('\nReleasing ... (RuntimeError)')
        safe_shutdown.release()

    log.debug('\nAcquiring ... (Final)')
    safe_shutdown.acquire()
    log.debug('\nReleasing ... (Final)')
    safe_shutdown.release()

    interrupt = False

    try:
        spawned_thread_safe_exit.release()
        log.debug('\nWaiting ...')
        while thread and not interrupt:
            pass
    except KeyboardInterrupt:
        interrupt = True
    finally:
        log.debug('\nThis console can now be closed')
            