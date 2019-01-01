# Introduction

This is the document of `rss2sql`

<!-- TOC depthFrom:2 -->

- [Specification](#specification)
    - [Classes](#classes)
        - [ToolKit](#toolkit)
        - [RSS](#rss)
        - [SQL](#sql)
    - [Configuration File](#configuration-file)
        - [Minimal configure](#minimal-configure)
        - [Using built-in reference table type instead of `ENUM` type](#using-built-in-reference-table-type-instead-of-enum-type)
        - [Common configure](#common-configure)
- [Usage](#usage)
    - [Within code](#within-code)
    - [Within commandline](#within-commandline)
    - [Discover mode](#discover-mode)

<!-- /TOC -->

## Specification

There are three `class` and a configuration file.

### Classes

#### ToolKit

This class define some useful static method to handle parsed feed

#### RSS

Just a representation of a single RSS feed item.

#### SQL

Creating table according to configuration file, call its **fetch** method to store data after that table created scuessfully.

### Configuration File

Thanks to the diversity of RSS feed, it is necessary to configure settings manually. Here is some examples:

#### Minimal configure

Store nothing but id.

```yaml
rss:
  url: "http://songshuhui.net/feed"
sql:
  tablename: "songshuhui"
  field:
    - name: id
      val: "x.get('id')"
      type: VARCHAR
      type_parameter: 64
      nullable: false
      primary_key: true
      autoincrement: false
```

#### Using built-in reference table type instead of `ENUM` type

Using `REFTABLE` instead of `ENUM`, then it will define a reference table with
field `id` as primary key and the field you named. 

For example:

```yaml
rss:
  url: https://nyaa.si/?page=rss
sql:
  tablename: nyaa
  field:
    - name: id
      val: "x.get('id')"
      type: VARCHAR
      type_parameter: 256
      nullable: false
      primary_key: true
      autoincrement: false
    - name: cate
      val: "x.get('nyaa_category')"
      type: REFTABLE
      type_parameter:
        - VARCHAR
        - 20
```

It will create a reference table with field `id` and `cate`,
and in table `nyaa` the `cate` field is a `INT` type.

#### Common configure

```yaml
rss:
  url: "https://share.dmhy.org/topics/rss/rss.xml"
  proxies:
    https: "https://127.0.0.1:1080"
sql:
  tablename: "dmhy"
  field:
    - name: id
      val: "x.get('id')"
      type: VARCHAR
      type_parameter: 256
      nullable: false
      primary_key: true
      autoincrement: false
    - name: title
      val: "x.get('title')"
      type: TEXT
    - name: link
      val: "x.get('link')"
      type: TEXT
    - name: pubtime
      val: "ToolKit.struct_time_To_datetime(x.get('published_parsed'))"
      type: TIMESTAMP
      index: true
    - name: summary
      val: "x.get('summary')"
      type: TEXT
```

Just remember the **x** in `val` denotes the *dict* instance of an item which parsed by `feedparser` library

## Usage

### Within code

```python
from rss2sql import SQL
SQL('/path/to/configuration','uri://of:your@own/database').fetch()
```

### Within commandline

```bash
python rss2sql.py -c /path/to/configuration -d uri://of:your@own/database --hide_banner
```

### Discover mode

Configuration file is needed, omit the field section, and run

```bash
python rss2sql.py -c /path/to/configuration  --discover
```

the configuration file should look like

```yaml
rss:
  url: http://songshuhui.net/feed
sql:
  tablename: nyaa
```