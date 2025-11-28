from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from dataclasses import dataclass
from typing import List, Optional
import traceback


from flasgger import Swagger

from flask_jwt_extended import JWTManager, create_access_token, jwt_required


app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///livros.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "segredo-super-seguro"

db = SQLAlchemy(app)
jwt = JWTManager(app)
swagger = Swagger(app)



livro_categoria = db.Table(
    "livro_categoria",
    db.Column("livro_id", db.Integer, db.ForeignKey("livros.id"), primary_key=True),
    db.Column("categoria_id", db.Integer, db.ForeignKey("categorias.id"), primary_key=True)
)

from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)

class Autor(db.Model):
    __tablename__ = "autores"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)

    livros = relationship("Livro", back_populates="autor", cascade="all, delete-orphan")
    perfil = relationship("AutorPerfil", uselist=False, back_populates="autor", cascade="all, delete-orphan")


class AutorPerfil(db.Model):
    __tablename__ = "autores_perfil"
    id = db.Column(db.Integer, primary_key=True)
    biografia = db.Column(db.String(500))
    data_nascimento = db.Column(db.String(20))
    autor_id = db.Column(db.Integer, db.ForeignKey("autores.id"), unique=True)
    autor = relationship("Autor", back_populates="perfil")


class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), nullable=False, unique=True)
    livros = relationship("Livro", secondary=livro_categoria, back_populates="categorias")


class Livro(db.Model):
    __tablename__ = "livros"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    ano = db.Column(db.Integer)
    autor_id = db.Column(db.Integer, db.ForeignKey("autores.id"))
    autor = relationship("Autor", back_populates="livros")
    categorias = relationship("Categoria", secondary=livro_categoria, back_populates="livros")
    

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(120), nullable=False)





@dataclass
class LivroDTO:
    id: int
    titulo: str
    autor: str
    categorias: List[str]
    ano: Optional[int] = None


@dataclass
class AutorDTO:
    id: int
    nome: str
    quantidade_livros: int
    biografia: Optional[str] = None
    data_nascimento: Optional[str] = None



class LivroMapper:
    @staticmethod
    def to_dto(livro: Livro) -> LivroDTO:
        categorias = [c.nome for c in livro.categorias] if livro.categorias else []
        return LivroDTO(
            id=livro.id,
            titulo=livro.titulo,
            autor=livro.autor.nome if livro.autor else "Desconhecido",
            categorias=categorias,
            ano=livro.ano
        )

    @staticmethod
    def from_dict(data: dict):
        return {
            "titulo": data.get("titulo"),
            "autor_nome": data.get("autor"),
            "categorias": data.get("categorias", []),
            "ano": data.get("ano")
        }


class AutorMapper:
    @staticmethod
    def to_dto(autor: Autor) -> AutorDTO:
        perfil = autor.perfil
        return AutorDTO(
            id=autor.id,
            nome=autor.nome,
            quantidade_livros=len(autor.livros),
            biografia=perfil.biografia if perfil else None,
            data_nascimento=perfil.data_nascimento if perfil else None
        )


class LivroRepository:
    @staticmethod
    def get_all():
        return Livro.query.all()

    @staticmethod
    def get_by_id(id: int):
        return Livro.query.get(id)

    @staticmethod
    def add(titulo: str, autor_nome: str, categorias: List[str], ano: int = None):
        autor = Autor.query.filter_by(nome=autor_nome).first()
        if not autor:
            autor = Autor(nome=autor_nome)
            db.session.add(autor)

        categorias_objs = []
        for c in categorias:
            cat = Categoria.query.filter_by(nome=c).first()
            if not cat:
                cat = Categoria(nome=c)
                db.session.add(cat)
            categorias_objs.append(cat)

        novo = Livro(titulo=titulo, autor=autor, categorias=categorias_objs, ano=ano)
        db.session.add(novo)
        db.session.commit()
        return novo

    @staticmethod
    def update(id: int, titulo=None, autor_nome=None, categorias=None, ano=None):
        livro = Livro.query.get(id)
        if not livro:
            return None

        if titulo is not None:
            livro.titulo = titulo

        if ano is not None:
            livro.ano = ano

        if autor_nome is not None:
            autor = Autor.query.filter_by(nome=autor_nome).first()
            if not autor:
                autor = Autor(nome=autor_nome)
                db.session.add(autor)
            livro.autor = autor

        if categorias is not None:
            nova_lista = []
            for c in categorias:
                cat = Categoria.query.filter_by(nome=c).first()
                if not cat:
                    cat = Categoria(nome=c)
                    db.session.add(cat)
                nova_lista.append(cat)
            livro.categorias = nova_lista

        db.session.commit()
        return livro

    @staticmethod
    def delete(id: int):
        livro = Livro.query.get(id)
        if livro:
            db.session.delete(livro)
            db.session.commit()
            return True
        return False


class AutorRepository:
    @staticmethod
    def get_all():
        return Autor.query.all()

    @staticmethod
    def get_by_id(id: int):
        return Autor.query.get(id)

    @staticmethod
    def add(nome: str, biografia=None, data_nascimento=None):
        autor = Autor(nome=nome)
        db.session.add(autor)
        db.session.flush()

        if biografia or data_nascimento:
            perfil = AutorPerfil(biografia=biografia, data_nascimento=data_nascimento, autor=autor)
            db.session.add(perfil)

        db.session.commit()
        return autor

    @staticmethod
    def delete(id: int):
        autor = Autor.query.get(id)
        if autor:
            db.session.delete(autor)
            db.session.commit()
            return True
        return False



def validar_dados_livro(data, require_all=True):
    erros = []
    if not isinstance(data, dict):
        return ["JSON inválido"]

    if require_all:
        if not data.get("titulo"):
            erros.append("Campo 'titulo' é obrigatório")
        if not data.get("autor"):
            erros.append("Campo 'autor' é obrigatório")

    if "categorias" in data and not isinstance(data["categorias"], list):
        erros.append("'categorias' deve ser lista")

    return erros


def validar_dados_autor(data):
    if not isinstance(data, dict):
        return ["JSON inválido"]
    if not data.get("nome"):
        return ["Campo 'nome' é obrigatório"]
    return []




@app.route("/")
def home():
    try:
        return render_template("index.html")
    except:
        return jsonify({"mensagem": "API de Livros funcionando."})




@app.route("/livros", methods=["GET"])
@jwt_required()
def get_livros():
    livros = LivroRepository.get_all()
    return jsonify([LivroMapper.to_dto(l).__dict__ for l in livros])


@app.route("/livros/<int:id>", methods=["GET"])
@jwt_required()
def get_livro(id):
    livro = LivroRepository.get_by_id(id)
    if livro:
        return jsonify(LivroMapper.to_dto(livro).__dict__)
    return jsonify({"erro": "Livro não encontrado"}), 404


@app.route("/livros", methods=["POST"])
@jwt_required()
def post_livro():
    data = request.get_json()
    erros = validar_dados_livro(data)
    if erros:
        return jsonify({"erros": erros}), 400

    payload = LivroMapper.from_dict(data)
    try:
        livro = LivroRepository.add(
            titulo=payload["titulo"],
            autor_nome=payload["autor_nome"],
            categorias=payload["categorias"],
            ano=payload["ano"]
        )
        return jsonify(LivroMapper.to_dto(livro).__dict__), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


@app.route("/livros/<int:id>", methods=["PUT"])
@jwt_required()
def put_livro(id):
    data = request.get_json()
    payload = LivroMapper.from_dict(data)

    livro = LivroRepository.update(
        id=id,
        titulo=payload.get("titulo"),
        autor_nome=payload.get("autor_nome"),
        categorias=payload.get("categorias"),
        ano=payload.get("ano")
    )
    if livro:
        return jsonify(LivroMapper.to_dto(livro).__dict__)
    return jsonify({"erro": "Livro não encontrado"}), 404


@app.route("/livros/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_livro(id):
    if LivroRepository.delete(id):
        return jsonify({"mensagem": "Livro removido"})
    return jsonify({"erro": "Livro não encontrado"}), 404




@app.route("/autores", methods=["GET"])
@jwt_required()
def get_autores():
    autores = AutorRepository.get_all()
    return jsonify([AutorMapper.to_dto(a).__dict__ for a in autores])


@app.route("/autores/<int:id>", methods=["GET"])
@jwt_required()
def get_autor(id):
    autor = AutorRepository.get_by_id(id)
    if autor:
        return jsonify(AutorMapper.to_dto(autor).__dict__)
    return jsonify({"erro": "Autor não encontrado"}), 404


@app.route("/autores", methods=["POST"])
@jwt_required()
def post_autor():
    data = request.get_json()
    erros = validar_dados_autor(data)
    if erros:
        return jsonify({"erros": erros}), 400

    try:
        autor = AutorRepository.add(
            nome=data["nome"],
            biografia=data.get("biografia"),
            data_nascimento=data.get("data_nascimento")
        )
        return jsonify(AutorMapper.to_dto(autor).__dict__), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": str(e)}), 500


@app.route("/autores/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_autor(id):
    if AutorRepository.delete(id):
        return jsonify({"mensagem": "Autor removido"})
    return jsonify({"erro": "Autor não encontrado"}), 404


@app.route("/categorias", methods=["GET"])
@jwt_required()
def get_categorias():
    cats = Categoria.query.all()
    return jsonify([
        {"id": c.id, "nome": c.nome, "quantidade_livros": len(c.livros)}
        for c in cats
    ])


@app.route("/categorias", methods=["POST"])
@jwt_required()
def post_categoria():
    data = request.get_json()
    if not data or not data.get("nome"):
        return jsonify({"erro": "Campo 'nome' é obrigatório"}), 400

    nome = data["nome"]
    if Categoria.query.filter_by(nome=nome).first():
        return jsonify({"erro": "Categoria já existe"}), 400

    cat = Categoria(nome=nome)
    db.session.add(cat)
    db.session.commit()
    return jsonify({"id": cat.id, "nome": cat.nome}), 201



from werkzeug.security import generate_password_hash, check_password_hash

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username")
    email = data.get("email")
    senha = data.get("senha")

    if not username or not email or not senha:
        return jsonify({"erro": "username, email e senha são obrigatórios"}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"erro": "Este email já está cadastrado"}), 400

    senha_hash = generate_password_hash(senha)

    novo = Usuario(username=username, email=email, senha=senha_hash)
    db.session.add(novo)
    db.session.commit()

    return jsonify({
        "mensagem": "Usuário registrado com sucesso",
        "id": novo.id,
        "username": novo.username,
        "email": novo.email
    }), 201



@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    email = data.get('email')
    senha = data.get('senha')

 
    user = Usuario.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.senha, senha):
        return jsonify({"msg": "Credenciais inválidas"}), 401

    
    access_token = create_access_token(identity=str(user.id))

    return jsonify({"access_token": access_token}), 200


@app.route("/livros-seguro", methods=["GET"])
@jwt_required()
def livros_seguro():
    livros = LivroRepository.get_all()
    return jsonify([LivroMapper.to_dto(l).__dict__ for l in livros])




if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(port=5000, host="localhost", debug=True)
