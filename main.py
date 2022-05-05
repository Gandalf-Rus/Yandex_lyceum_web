from flask import Flask, render_template, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import Api
from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from requests import get

from data import db_session, recipes_api
from data.users import User
from data.news import News
from forms.new import NewsForm
from forms.user import RegisterForm
from forms.login_form import LoginForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)


def main():
    db_session.global_init("db/blogs.db")
    api.add_resource(recipes_api.NewsListResource, '/api/recipes')
    api.add_resource(recipes_api.NewsResource, '/api/recipes/<int:news_id>')

    @login_manager.user_loader
    def load_user(user_id):
        db_sess = db_session.create_session()
        return db_sess.query(User).get(user_id)

    @app.route("/")
    def index():
        """
        Главня страница
        """
        db_sess = db_session.create_session()
        if current_user.is_authenticated:
            news = db_sess.query(News).filter(
                (News.user == current_user) | (News.is_private != True))
        else:
            news = db_sess.query(News).filter(News.is_private != True)
        return render_template("index.html", news=news)

    @app.route('/recipes/<int:id>')
    def recipes(id):
        request = get(f'http://127.0.0.1:8080/api/recipes/{id}').json()
        if "message" in request.keys():
            return render_template("recipes.html", message="Простите, но данного рецепта не было обнаружено")

        if request["recipes"]["is_private"] is True:
            if current_user.is_authenticated is False:
                return render_template("recipes.html", message="Простите, но у вас нет доступа к этому рецепту")
            elif current_user.id != request["recipes"]["user_id"]:
                return render_template("recipes.html", message="Простите, но у вас нет доступа к этому рецепту")
        return render_template("recipes.html", recipes=request["recipes"], message=None)

    @app.route('/register', methods=['GET', 'POST'])
    def reqister():
        """
        Форма регистрации
        """
        form = RegisterForm()
        if form.validate_on_submit():
            if form.password.data != form.password_again.data:
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Пароли не совпадают")
            db_sess = db_session.create_session()
            if db_sess.query(User).filter(User.email == form.email.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")
            user = User(
                name=form.name.data,
                email=form.email.data,
                about=form.about.data
            )
            user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            login_user(user)
            return redirect('/')
        return render_template('register.html', title='Регистрация', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
        Форма входа
        """
        form = LoginForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form)
        return render_template('login.html', title='Авторизация', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        """
        Выход из аккаунта
        """
        logout_user()
        return redirect("/")

    @app.route('/news', methods=['GET', 'POST'])
    @login_required
    def add_news():
        form = NewsForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            news = News()
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            current_user.news.append(news)
            db_sess.merge(current_user)
            db_sess.commit()
            return redirect('/')
        return render_template('news.html', title='Добавление новости',
                               form=form)

    @app.route('/news/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_news(id):
        form = NewsForm()
        if request.method == "GET":
            db_sess = db_session.create_session()
            news = db_sess.query(News).filter(News.id == id,
                                              News.user == current_user
                                              ).first()
            if news:
                form.title.data = news.title
                form.content.data = news.content
                form.is_private.data = news.is_private
            else:
                abort(404)
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            news = db_sess.query(News).filter(News.id == id,
                                              News.user == current_user
                                              ).first()
            if news:
                news.title = form.title.data
                news.content = form.content.data
                news.is_private = form.is_private.data
                db_sess.commit()
                return redirect('/')
            else:
                abort(404)
        return render_template('news.html',
                               title='Редактирование новости',
                               form=form
                               )

    @app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
    @login_required
    def news_delete(id):
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            db_sess.delete(news)
            db_sess.commit()
        else:
            abort(404)
        return redirect('/')

    app.run(port=8080)


if __name__ == '__main__':
    main()
