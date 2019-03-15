import configparser
import logging

log = logging.getLogger(__name__)

class Config:
    def __init__(self, config_file):
        self.config_file = config_file

        config = configparser.ConfigParser(interpolation=None)
        config.read(config_file, encoding='utf-8')

        confsections = {"Credentials", "Permissions", "Chat", "Bot"}.difference(config.sections())
        if confsections:
            raise Exception("One or more required config sections are missing. {}".format(confsections))

        self.token = config.get('Credentials', 'Token', fallback=ConfigDefaults.token)

        self.owner_id = config.get('Permissions', 'OwnerID', fallback=ConfigDefaults.owner_id)

        self.command_prefix = config.get('Chat', 'CommandPrefix', fallback=ConfigDefaults.command_prefix)

        self.debug_level = config.get('Bot', 'DebugLevel', fallback=ConfigDefaults.debug_level)

        self.run_checks()

    def run_checks(self):
        """
        Validation logic for bot settings.
        """

        if not self.token:
            raise Exception("No bot token was specified in the config.")

        if self.owner_id:
            self.owner_id = self.owner_id.lower()

            if self.owner_id.isdigit():
                if int(self.owner_id) < 10000:
                    raise Exception("An invalid OwnerID was set: {}".format(self.owner_id))
                self.owner_id = int(self.owner_id)

            elif self.owner_id == 'auto':
                pass # defer to async check

            else:
                self.owner_id = None

        if not self.owner_id:
            raise Exception("No OwnerID was set. Please set the OwnerID option in {}".format(self.config_file))

        if hasattr(logging, self.debug_level.upper()):
            self.debug_level = getattr(logging, self.debug_level.upper())
        else:
            log.warning("Invalid DebugLevel option \"{}\" given, falling back to INFO".format(self.debug_level))
            self.debug_level = logging.INFO

class ConfigDefaults:
    owner_id = None

    token = None

    command_prefix = '!'
    debug_level = 'DEBUG'

    config_file = 'config/config.ini'