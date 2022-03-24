from flask import Flask, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'


def main():
    @app.route('/')
    @app.route('/index')
    def index():
        return render_template('index.html')
    app.run()


if __name__ == '__main__':
    main()
