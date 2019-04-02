import asyncio
import logging
import sys
from bot import logger
from bot.bot import ModuBot
from bot.config import Config, ConfigDefaults
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

    loop = asyncio.get_event_loop()

    config = Config(ConfigDefaults.config_file)
    bot = ModuBot(loop=loop, conf=config, loghandlerlist=[sh], max_messages=10000)
    loop.run_until_complete(bot.load_modules([('default',{}), ('permission',{})]))

    def logouthandler(sig, stackframe=None):
        log.info(sig)
        bot.logout()

    if system() == 'Windows':
        try:
            from win32.win32api import SetConsoleCtrlHandler
            SetConsoleCtrlHandler(logouthandler, True)
        except ImportError:
            version = '.'.join(map(str, sys.version_info))
            log.warn('pywin32 not installed for Python {}. Please stop the bot using KeyboardInterrupt instead of the close button.'.format(version))
    
    else:
        import signal
        signal.signal(signal.SIGTERM, logouthandler)

    try:
        bot.run()
    except (KeyboardInterrupt, RuntimeError):
        log.info('\nShutting down ... (KeyboardInterrupt)')
        bot.logout()