from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from sqlalchemy import ForeignKey, desc
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
import os

app = Flask(__name__)
# app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
# Move the line above to the Config Var (Enviromental variables to the configuration Menu in Heroku):
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB:
# LOCAL - SQLite:
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'  # This line was to use SQLite
# HEROKU - PostgreSQL:
# The next line is the configuration of Postgres SQL in Heroku:
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL_1")  # The "," is for when running Locally
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", 'sqlite:///blog.db')  # The "," is for when running Locally

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

## GRAVATAR
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES
# Create the User Table
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost/Comment class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")  # This is not a "column" in the "blog_posts" table at the DB. Its how the 2 tables are related


    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "comments" refers to the posts property in the User class.
    author = relationship("User", back_populates="comments")  # This is not a "column" in the table at the DB

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the User object, the "comments" refers to the posts property in the BlogPost class.
    parent_post = relationship("BlogPost", back_populates="comments")  # This is not a "column" in the table at the DB

db.create_all()



# ------------------------------------- LOGIN MANAGER ------------------------------------- #
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------------------------------------------------------------------------- #


@app.route('/')
def get_all_posts():
    # posts = BlogPost.query.all()
    posts = BlogPost.query.order_by(desc(BlogPost.id)).all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)


@app.route('/register', methods=['GET', 'POST'])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        email = register_form.email.data
        hashed_and_salted_password = generate_password_hash(
            password=register_form.password.data,
            method="pbkdf2:sha256",
            salt_length=8)
        name = register_form.name.data
        exists_user = User.query.filter_by(email=email).first()
        if exists_user:
            flash('You have already signed up with that email. Please Login in instead.')
            return  redirect(url_for('login'))
        else:
            new_user = User(
                email=email,
                password=hashed_and_salted_password,
                name=name
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=register_form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        form_password = login_form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User does not exist. Please try again')
        else:
            if check_password_hash(user.password, form_password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Invalid credentials. Try again')

    return render_template("login.html", form=login_form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.filter_by(post_id=post_id).all()
    print(comments)

    if comment_form.validate_on_submit():
        new_comment = Comment(
            text=comment_form.comment.data,
            author_id=current_user.id,
            post_id=post_id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("post.html", post=requested_post, all_post_comments=comments, logged_in=current_user.is_authenticated, form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)

# def admin_only(function):
#     def check_admin(*args, **kwargs):
#         print(current_user.id)
#         if current_user.id == 1:
#             print("if")
#             function(*args, **kwargs)
#         else:
#             print("else")
#             return "Forbidden", 403
#     return check_admin
#
#     #Create admin-only decorator

def admin_only(f):
    """THIS IS ANGELAS VERSION. I DIDN'T UNDERSTAND WHAT THE @WRAPS FUNCTION DOES
    https://realpython.com/primer-on-python-decorators/#who-are-you-really"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function



@app.route("/new-post", methods=['GET', 'POST'])
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=5000)
if __name__ == "__main__":
    app.run(debug=True)
