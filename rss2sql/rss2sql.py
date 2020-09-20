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

    @staticmethod
    def IEC_prefix_To_Bytes(string):
        '''
        Convert `1 KiB` to `1024`
        '''
        content = string.split(' ')
        value, level = content[0], content[-1]
        power = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB',
                 'YiB'].index(level)
        return float(value)*1024**power

    @staticmethod
    def Hexstring_To_Bytes(string):
        from binascii import unhexlify
        return unhexlify(string)


class RSS:
    def __init__(self, *args, **kwargs):
        _ = args
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __repr__(self):
        return str(self.__dict__)


class SQL:
    _tables = []

    def __init__(self, conf, dburi='sqlite:///:memory:', echo_sql=False):
        self.logger = LOGGER.getChild('SQL')
        from os.path import isfile
        if isinstance(conf, str) and isfile(conf):
            with open(conf) as fp:
                conf = fp.read()
        self.config = yaml.full_load(conf)
        self.config_parse()
        if self.config['sql'].get('field', None):
            from sqlalchemy.orm import mapper, sessionmaker
            self.config['sql']['engine'] = sqlalchemy.create_engine(
                dburi, echo=echo_sql)
            META.create_all(self.config['sql']['engine'])
            for tbcls, tbinstance in self._tables:
                mapper(tbcls, tbinstance)
            Session = sessionmaker(bind=self.config['sql']['engine'])
            self._session = Session()
        else:
            self.logger.info('sql:field not defined')

    @property
    def tablename(self):
        return self.config['sql']['tablename']

    def query(self, *args, **kwargs):
        return self._session.query(*args, **kwargs)

    def merge(self, *args, **kwargs):
        return self._session.merge(*args, **kwargs)

    def commit(self, *args, **kwargs):
        return self._session.commit(*args, **kwargs)

    def quit(self, *args, **kwargs):
        self.commit()
        return self._session.close(*args, **kwargs)

    def _request_sql_type(self, sql_type):
        ret = getattr(sqlalchemy, sql_type, None)

        if ret is None:
            self.logger.critical('%s is not a valid SQL type', sql_type)
            raise TypeError('SQL Type invalid')

        return ret

    def _field_parse(self, field_def):
        req_type = field_def.get('type', 'TEXT')
        params = field_def.get('type_parameter', None)
        if req_type.upper() == 'REFTABLE':
            ref_tablename = '%s_ref_%s' % (self.tablename, field_def['name'])
            req_ref_type = params[0] if isinstance(params, list) else params
            ref_params = params[1] if isinstance(params, list) else None
            sql_type = self._request_sql_type(req_ref_type)
            t_ref = sql_type(ref_params) if ref_params else sql_type()

            pkcol = sqlalchemy.Column('id', sqlalchemy.INT, primary_key=True)
            refcol = sqlalchemy.Column(field_def['name'], t_ref, unique=True)

            ref_cls = type('REF_%s' % field_def['name'], (RSS, ), {})
            self._tables.append((
                ref_cls,
                sqlalchemy.Table(ref_tablename, META, pkcol, refcol),
            ))
            cargs = (
                field_def['name'],
                sqlalchemy.INT,
                sqlalchemy.ForeignKey('%s.id' % ref_tablename),
            )
            field_def['nullable'] = False

            def evalfunc(x):
                x = eval(field_def['val'])
                val = {field_def['name']: x}
                ref = self.query(ref_cls).filter_by(**val).first()
                if ref is None:
                    self.merge(ref_cls(**{field_def['name']: x}))
                    self.commit()
                    ref = self.query(ref_cls).filter_by(**val).first()
                return ref.id
        else:
            sql_type = self._request_sql_type(req_type)

            evalfunc = lambda x: eval(field_def['val'])
            if isinstance(params, list):
                sql_col = sql_type(*params)
            else:
                sql_col = sql_type(params) if params else sql_type()
            cargs = (field_def['name'], sql_col)

        kwargs = {
            name: field_def.get(name, default)
            for name, default in [
                ('nullable', True),
                ('primary_key', False),
                ('autoincrement', False),
                ('index', False),
                ('unique', False),
            ]
        }

        return (
            field_def['name'],
            evalfunc,
            sqlalchemy.Column(*cargs, **kwargs),
        )

    def config_parse(self):
        fields = [
            self._field_parse(f) for f in self.config['sql'].get('field', [])
        ]
        self.config['rss']['explain'] = [(i[0], i[1]) for i in fields]
        self._tables.append((
            RSS,
            sqlalchemy.Table(self.tablename, META, *[i[2] for i in fields]),
        ))

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
            self.merge(
                RSS(
                    **{
                        name: func(feed)
                        for name, func in self.config['rss']['explain']
                    }))
            self.commit()

def entrypoint():
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

if __name__ == "__main__":
    entrypoint()
