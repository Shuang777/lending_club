""" Simple module that takes care of authentication configs

In the future this could be merged with logging configs.

TODO: add a password to MongoDB access
"""
import logging
import staticconf

auth_namespace = 'authentication'
auth_config = staticconf.NamespaceGetters(auth_namespace)

# ValueProxies for credentials that are populated once an authfile is loaded
lc_username = auth_config.get_string('lendingclub.username', None)
lc_password = auth_config.get_string('lendingclub.password', None)


def load_authfile(authfile):
    try:
        staticconf.YamlConfiguration(authfile, namespace=auth_namespace)
        logging.info("Loaded authfile: %s", authfile)
    except Exception as e:
        logging.warning("Failed to load authfile %s: %s", authfile, e)
