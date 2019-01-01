# RSS to SQL

Preserving your subscribed RSS feeds into a relational database.
View [docs](https://jsjyhzy.github.io/rss2sql/) for specification

## Installation

For now, download the zip acharive and install dependencies.
In the future, `pip install` maybe.

### Dependency

- `SQLAlchemy` and its connector friends (only if you need them)
- `feedparser`
- `requests`
- `PyYAML`

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
