import os
from flask import Flask, render_template, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import Api
from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from requests import get

from data import db_session, recipes_api
from data.users import User
from data.recipes import Recipes
from forms.add_and_change_form import AddingForm
from forms.user import RegisterForm
from forms.login_form import LoginForm
from tools.new_picture_name import give_picture_name

# config
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)


def main():
    db_session.global_init("db/blogs.db")
    api.add_resource(recipes_api.RecipesListResource, '/api/recipes')
    api.add_resource(recipes_api.RecipesResource, '/api/recipes/<int:recip_id>')

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
            recipes = db_sess.query(Recipes).filter(
                (Recipes.user == current_user) | (Recipes.is_private != True))
        else:
            recipes = db_sess.query(Recipes).filter(Recipes.is_private != True)
        return render_template("index.html", recipes=recipes)

    @app.route('/recipes/<int:id>')
    def recipes(id):
        """
        отображение рецепта
        :param id: id рецепта
        :return: страницу
        """

        requests = get(f'http://127.0.0.1:8080/api/recipes/{id}').json()
        if "message" in requests.keys():
            return render_template("recipes.html", message="Простите, но данного рецепта не было обнаружено")

        if requests["recipes"]["is_private"] is True:
            if current_user.is_authenticated is False:
                return render_template("recipes.html", message="Простите, но у вас нет доступа к этому рецепту")
            elif current_user.id != requests["recipes"]["user_id"]:
                return render_template("recipes.html", message="Простите, но у вас нет доступа к этому рецепту")
        return render_template("recipes.html", recipes=requests["recipes"], message=None)

    @app.route('/register', methods=['GET', 'POST'])
    def reqister():
        """
        Форма регистрации
        :return: страницу регистрации
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
        :return: главная страница
        """
        logout_user()
        return redirect("/")

    @app.route('/add_recipes', methods=['GET', 'POST'])
    @login_required
    def add_recip():
        form = AddingForm()
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            recipes = Recipes()
            photo = request.files['file']
            if photo.filename != "":
                name = give_picture_name()
                photo.save(name)
                recipes.image = name
            recipes.title = form.title.data
            recipes.content = form.content.data
            recipes.is_private = form.is_private.data
            current_user.recipes.append(recipes)
            db_sess.merge(current_user)
            db_sess.commit()
            return redirect('/')
        return render_template('add_change_recipes.html', title='Добавление рецепта', form=form)

    @app.route('/change_recipes/<int:id>', methods=['GET', 'POST'])
    @login_required
    def change_recip(id):
        form = AddingForm()
        if request.method == "GET":
            db_sess = db_session.create_session()
            recipes = db_sess.query(Recipes).filter(Recipes.id == id,
                                                    Recipes.user == current_user).first()
            if recipes:
                form.title.data = recipes.title
                form.content.data = recipes.content
                form.is_private.data = recipes.is_private
            else:
                abort(404)
        if form.validate_on_submit():
            db_sess = db_session.create_session()
            recipes = db_sess.query(Recipes).filter(Recipes.id == id, Recipes.user == current_user).first()
            if recipes:
                photo = request.files['file']
                if photo.filename != "":
                    if recipes.image is not None:
                        name = recipes.image
                        photo.save(name)
                    else:
                        name = give_picture_name()
                        photo.save(name)
                        recipes.image = name
                recipes.title = form.title.data
                recipes.content = form.content.data
                recipes.is_private = form.is_private.data
                db_sess.commit()
                return redirect('/')
            else:
                abort(404)
        return render_template('add_change_recipes.html', title='Редактирование рецепта', form=form)

    @app.route('/delete_recipes/<int:id>', methods=['GET', 'POST'])
    @login_required
    def delete_recipes(id):
        db_sess = db_session.create_session()
        recipes = db_sess.query(Recipes).filter(Recipes.id == id,
                                                Recipes.user == current_user
                                                ).first()
        if recipes:
            if recipes.image is not None:
                if recipes.image.replace("static/img/", "") in os.listdir("static/img"):
                    os.remove(recipes.image)
            db_sess.delete(recipes)
            db_sess.commit()
        else:
            abort(404)
        return redirect('/')

    app.run(port=8080)


if __name__ == '__main__':
    main()
