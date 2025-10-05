import os

# Exporta a aplicação Flask como "application" para servidores WSGI
from app import app as application

if __name__ == '__main__':
    from waitress import serve
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    serve(application, host=host, port=port)