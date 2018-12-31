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
    _tables = []

    def __init__(self, conf, dburi='sqlite:///:memory:', echo_sql=False):
        self.logger = LOGGER.getChild('SQL')
        from os.path import isfile
        if isinstance(conf, str) and isfile(conf):
            with open(conf) as fp:
                conf = fp.read()
        self.config = yaml.load(conf)
        self.config_parse()
        if self.config['sql'].get('field', None):
            from sqlalchemy.orm import mapper, sessionmaker
            self.config['sql']['engine'] = sqlalchemy.create_engine(
                dburi, echo=echo_sql)
            META.create_all(self.config['sql']['engine'])
            for tbcls, tbinstance in self._tables:
                mapper(tbcls, tbinstance)
            Session = sessionmaker(bind=self.config['sql']['engine'])
            self.session = Session()
        else:
            self.logger.info('sql:field not defined')

    @property
    def tablename(self):
        return self.config['sql']['tablename']

    def _field_parse(self, field_def):
        req_type = field_def.get('type', 'TEXT')
        params = field_def.get('type_parameter', None)
        if req_type.upper() == 'REFTABLE':
            ref_tablename = '%s_REF_%s' % (self.tablename, field_def['name'])
            pkcol = sqlalchemy.Column(
                'id',
                sqlalchemy.INT,
                primary_key=True,
                autoincrement=True,
                nullable=False,
            )
            req_ref_type = params[0] if isinstance(params, list) else params
            ref_params = params[1] if isinstance(params, list) else None
            sql_type = getattr(sqlalchemy, req_ref_type, None)
            if sql_type:
                t_refcol = sql_type(ref_params) if ref_params else sql_type()
                refcol = sqlalchemy.Column(
                    field_def['name'],
                    t_refcol,
                    unique=True,
                )
            else:
                self.logger.critical('%s is not a valid SQL type', req_type)
                raise TypeError('SQL Type invalid')
            ref_type = type('REF_%s' % field_def['name'], (RSS, ), {})
            self._tables.append((
                ref_type,
                sqlalchemy.Table(ref_tablename, META, pkcol, refcol),
            ))
            cargs = (
                field_def['name'],
                sqlalchemy.INT,
                sqlalchemy.ForeignKey('.'.join(
                    [ref_tablename, field_def['name']])),
            )
            field_def['nullable'] = False

            def evalfunc(x):
                x = eval(field_def['val'])
                ref = self.session.query(ref_type).filter_by(
                    **{
                        field_def['name']: x
                    }).first()
                if ref is None:
                    self.session.merge(ref_type(**{field_def['name']: x}))
                    self.session.commit()
                    ref = self.session.query(ref_type).filter_by(
                        **{
                            field_def['name']: x
                        }).first()
                return ref.id
        else:
            sql_type = getattr(sqlalchemy, req_type, None)
            if sql_type:
                evalfunc = lambda x: eval(field_def['val'])
                if isinstance(params, list):
                    sql_col = sql_type(*params)
                else:
                    sql_col = sql_type(params) if params else sql_type()
                cargs = (field_def['name'], sql_col)
            else:
                self.logger.critical('%s is not a valid SQL type', req_type)
                raise TypeError('SQL Type invalid')

        kwargs = {
            'nullable': field_def.get('nullable', True),
            'primary_key': field_def.get('primary_key', False),
            'autoincrement': field_def.get('autoincrement', False),
            'index': field_def.get('index', False),
            'unique': field_def.get('unique', False)
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
        self.config['sql']['table'] = sqlalchemy.Table(self.tablename, META,
                                                       *[i[2] for i in fields])
        self._tables.append((RSS, self.config['sql']['table']))

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
