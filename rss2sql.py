'''rss2sql.py

RSS to SQL toolkit
'''
import logging

import feedparser
import requests
import sqlalchemy
import yaml

LOGGER = logging.getLogger('rss2sql')
META = sqlalchemy.MetaData()


class ToolKit:
    @staticmethod
    def struct_time_To_datetime(st):
        from datetime import datetime
        from time import mktime
        return datetime.fromtimestamp(mktime(st))


class RSS:
    def __init__(self, *args, **kwargs):
        _ = args
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __repr__(self):
        return str(self.__dict__)


class SQL:
    def __init__(self, conf, dburi='sqlite:///:memory:', echo_sql=False):
        self.logger = LOGGER.getChild('SQL')
        self.config = self.config_parse(conf)
        if self.config['sql'].get('field', None):
            from sqlalchemy.orm import mapper, sessionmaker
            self.config['sql']['engine'] = sqlalchemy.create_engine(
                dburi, echo=echo_sql)
            META.create_all(self.config['sql']['engine'])
            mapper(RSS, self.config['sql']['table'])
            Session = sessionmaker(bind=self.config['sql']['engine'])
            self.session = Session()
        else:
            self.logger.info('sql:field not defined')

    def config_parse(self, conf):
        from os.path import isfile
        if isinstance(conf, str) and isfile(conf):
            with open(conf) as fp:
                conf = fp.read()
        config = yaml.load(conf)

        def field_parse(field_def):
            field_type = getattr(sqlalchemy, field_def.get('type', 'TEXT'))
            parameter = field_def.get('type_parameter', None)

            cargs = (
                field_def['name'],
                field_type(parameter) if parameter else field_type(),
            )

            kwargs = {
                'nullable': field_def.get('nullable', True),
                'primary_key': field_def.get('primary_key', False),
                'autoincrement': field_def.get('autoincrement', False),
                'index': field_def.get('index', False),
                'unique': field_def.get('unique', False)
            }

            return (
                field_def['name'],
                lambda x: eval(field_def['val']),
                sqlalchemy.Column(*cargs, **kwargs),
            )

        fields = [field_parse(f) for f in config['sql'].get('field', [])]
        config['rss']['explain'] = [(i[0], i[1]) for i in fields]
        config['sql']['table'] = sqlalchemy.Table(
            config['sql']['tablename'], META, *[i[2] for i in fields])

        return config

    @property
    def feeds(self):
        ret = requests.get(
            url=self.config['rss']['url'],
            proxies=self.config['rss'].get('proxies', {}))

        if not ret.ok:
            self.logger.critical('Request failed, code %s', ret.status_code)
            raise RuntimeError('Response %s' % ret.status_code)

        return feedparser.parse(ret.content)

    def fetch(self):
        for feed in self.feeds['entries']:
            self.session.merge(
                RSS(
                    **{
                        name: func(feed)
                        for name, func in self.config['rss']['explain']
                    }))
        self.session.commit()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c',
        dest='config',
        action='store',
        default=None,
        help='Path to configuration file',
    )
    parser.add_argument(
        '-d',
        dest='uri',
        action='store',
        default=None,
        help='URI of database',
    )
    parser.add_argument(
        '--discover',
        dest='discover',
        action='store_const',
        const=True,
        default=False,
        help='Discover the RSS feed entry struct',
    )
    parser.add_argument(
        '--hide_banner',
        dest='hide',
        action='store_const',
        const=True,
        default=False,
    )

    logging.basicConfig()

    args = parser.parse_args()

    if not args.hide:
        print(__doc__)

    if args.config is not None and args.discover:
        LOGGER.warning('Discover mode activated, ignoring database URI.')
        from pprint import pprint
        pprint(SQL(args.config).feeds['entries'][0])
        exit(0)

    if args.config is None or args.uri is None:
        exit(1)

    SQL(args.config, args.uri).fetch()
