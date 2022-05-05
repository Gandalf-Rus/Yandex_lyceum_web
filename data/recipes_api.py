from flask import jsonify
from flask_restful import abort, Resource, reqparse

from data import db_session
from data.recipes import Recipes


def abort_if_recipes_not_found(recip_id):
    session = db_session.create_session()
    recipes = session.query(Recipes).get(recip_id)
    if not recipes:
        abort(404, message=f"recipes {recip_id} not found")


class RecipesResource(Resource):
    def get(self, recip_id):
        abort_if_recipes_not_found(recip_id)
        session = db_session.create_session()
        recipes = session.query(Recipes).get(recip_id)
        return jsonify({'recipes': recipes.to_dict(
            only=('title', 'content', 'user_id', 'is_private', "created_date", "user.name", "id"))})

    def delete(self, recip_id):
        abort_if_recipes_not_found(recip_id)
        session = db_session.create_session()
        recipes = session.query(Recipes).get(recip_id)
        session.delete(recipes)
        session.commit()
        return jsonify({'success': 'OK'})


parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('content', required=True)
parser.add_argument('is_private', required=True, type=bool)
parser.add_argument('user_id', required=True, type=int)


class RecipesListResource(Resource):
    def get(self):
        session = db_session.create_session()
        recipes = session.query(Recipes).all()
        return jsonify({'recipes': [item.to_dict(
            only=('title', 'content', 'user_id', 'is_private', "created_date", "user.name", "id")) for item in recipes]})

    def post(self):
        args = parser.parse_args()
        session = db_session.create_session()
        recipes = Recipes(
            title=args['title'],
            content=args['content'],
            user_id=args['user_id'],
            is_private=args['is_private']
        )
        session.add(recipes)
        session.commit()
        return jsonify({'success': 'OK'})
