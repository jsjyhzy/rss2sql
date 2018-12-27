'''rss2sql.py

RSS to SQL toolkit
'''
import logging

import feedparser
import requests
import sqlalchemy
import yaml

LOGGER = logging.getLogger('grs')
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
        self.logger = LOGGER.getChild('GRS')
        self.config = self.config_parse(conf)

        from sqlalchemy.orm import mapper, sessionmaker
        self.config['sql']['engine'] = sqlalchemy.create_engine(
            dburi, echo=echo_sql)
        META.create_all(self.config['sql']['engine'])
        mapper(RSS, self.config['sql']['table'])
        Session = sessionmaker(bind=self.config['sql']['engine'])
        self.session = Session()

    def config_parse(self, conf):
        from os.path import isfile
        if isinstance(conf, str) and isfile(conf):
            with open(conf) as fp:
                conf = fp.read()
        config = yaml.load(conf)

        def field_parse(field_def):
            val = field_def['val']
            name = field_def['name']

            field_type = field_def.get('type', 'TEXT')
            field_type_parameter = field_def.get('type_parameter', None)
            field_type_class = getattr(sqlalchemy, field_type)(
                field_type_parameter) if field_type_parameter else getattr(
                    sqlalchemy, field_type)

            kwargs = {
                'nullable': field_def.get('nullable', True),
                'primary_key': field_def.get('primary_key', False),
                'autoincrement': field_def.get('autoincrement', False),
                'index': field_def.get('index', False),
                'unique': field_def.get('unique', False)
            }

            return ((name, lambda x: eval(val)),
                    sqlalchemy.Column(name, field_type_class, **kwargs))

        columns = [field_parse(f)[1] for f in config['sql'].get('field', [])]
        config['sql']['table'] = sqlalchemy.Table(config['sql']['tablename'],
                                                  META, *columns)

        config['rss']['explain'] = [
            field_parse(f)[0] for f in config['sql'].get('field', [])
        ]

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
    print(__doc__)
