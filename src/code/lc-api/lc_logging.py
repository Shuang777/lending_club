import ConfigParser
import datetime
import logging
import logging.handlers
import os

CONFIG_FILENAME = 'lendingclub.conf'
LOGGING_SECTION = 'logging'
FILENAME_KEY = 'filename'
DIRECTORY_KEY = 'directory'
LOGLEVEL_KEY = 'loglevel'
FROMADDR_KEY = 'fromaddr'
TOADDR_KEY = 'toaddr'
MAILPORT_KEY = 'mailport'
MAILHOST_KEY = 'mailhost'

LOGGING_DEFAULTS = {
    FILENAME_KEY: 'lendingclub.log',
    DIRECTORY_KEY: './logs/',
    LOGLEVEL_KEY: 'DEBUG',
}


def init_logging(config_file=CONFIG_FILENAME):

    config = ConfigParser.ConfigParser()
    configs_read = config.read(config_file)
    logfilename = ''
    logdirectory = ''
    loglevelstr = ''
    logtoaddr = ''
    logfromaddr = ''
    logmailport = ''
    logmailhost = ''

    if LOGGING_SECTION in config.sections():
        logfilename = config.get(LOGGING_SECTION,
                                 FILENAME_KEY)
        logdirectory = config.get(LOGGING_SECTION,
                                  DIRECTORY_KEY)
        loglevelstr = config.get(LOGGING_SECTION,
                                 LOGLEVEL_KEY)
        logtoaddr = config.get(LOGGING_SECTION,
                               TOADDR_KEY)
        logfromaddr = config.get(LOGGING_SECTION,
                                 FROMADDR_KEY)
        logmailhost = config.get(LOGGING_SECTION,
                                 MAILHOST_KEY)
        logmailport = config.get(LOGGING_SECTION,
                                 MAILPORT_KEY)
    if not logfilename:
        logfilename = LOGGING_DEFAULTS[FILENAME_KEY]
    if not logdirectory:
        logdirectory = LOGGING_DEFAULTS[DIRECTORY_KEY]
    if not loglevelstr:
        loglevelstr = LOGGING_DEFAULTS[LOGLEVEL_KEY]
    logfilename = os.path.join(logdirectory, logfilename)
    if not os.path.exists(logdirectory):
        os.makedirs(logdirectory)

    loglevel = getattr(logging, loglevelstr, logging.NOTSET)

    # Initialize logging LOGLEVEL to file
    logging.basicConfig(filename=logfilename,
                        level=loglevel,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='[%Y-%m-%d %H:%M:%S]')
    if not configs_read:
        logging.error('Error reading conf file %s', CONFIG_FILENAME)
    logging.debug(FILENAME_KEY + '=' + logfilename)
    logging.debug(DIRECTORY_KEY + '=' + logdirectory)
    logging.debug(LOGLEVEL_KEY + '=' + loglevelstr)
    logging.debug(MAILHOST_KEY + '=' + logmailhost)
    logging.debug(MAILPORT_KEY + '=' + logmailport)
    logging.debug(FROMADDR_KEY + '=' + logfromaddr)
    logging.debug(TOADDR_KEY + '=' + logtoaddr)

    logger = logging.getLogger()

    # Initialize logging INFO to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Initialize logging CRITICAL errors via email
    if logtoaddr and logfromaddr and logmailhost:
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        smtp_handler = logging.handlers.SMTPHandler(
            mailhost=(logmailhost, logmailport),
            fromaddr=logfromaddr,
            toaddrs=[logtoaddr],
            subject='LC-API Critical failure [%s]' % now_str)
        smtp_handler.setLevel(logging.CRITICAL)
        logger.addHandler(smtp_handler)
        logging.debug('smtp handler added')
