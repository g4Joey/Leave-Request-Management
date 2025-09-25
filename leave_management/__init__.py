try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    # pymysql not available, likely using SQLite in development
    pass