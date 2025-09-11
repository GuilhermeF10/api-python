from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from dataclasses import dataclass

app = Flask(__name__)
CORS(app)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///livros.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Autor(db.Model):
    __tablename__ = "autores"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

    livros = relationship("Livro", back_populates="autor", cascade="all, delete")

class Livro(db.Model):
    __tablename__ = "livros"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey("autores.id"))

    autor = relationship("Autor", back_populates="livros")



@dataclass
class LivroDTO:
    id: int
    titulo: str
    autor: str

    @staticmethod
    def from_model(livro: Livro):
        return LivroDTO(
            id=livro.id,
            titulo=livro.titulo,
            autor=livro.autor.nome if livro.autor else "Desconhecido"
        )


class LivroRepository:
    @staticmethod
    def get_all():
        return Livro.query.all()

    @staticmethod
    def get_by_id(id):
        return Livro.query.get(id)

    @staticmethod
    def add(titulo, autor_nome):
        autor = Autor.query.filter_by(nome=autor_nome).first()
        if not autor:
            autor = Autor(nome=autor_nome)
            db.session.add(autor)

        novo_livro = Livro(titulo=titulo, autor=autor)
        db.session.add(novo_livro)
        db.session.commit()
        return novo_livro

    @staticmethod
    def update(id, titulo=None, autor_nome=None):
        livro = Livro.query.get(id)
        if livro:
            if titulo:
                livro.titulo = titulo
            if autor_nome:
                autor = Autor.query.filter_by(nome=autor_nome).first()
                if not autor:
                    autor = Autor(nome=autor_nome)
                    db.session.add(autor)
                livro.autor = autor
            db.session.commit()
        return livro

    @staticmethod
    def delete(id):
        livro = Livro.query.get(id)
        if livro:
            db.session.delete(livro)
            db.session.commit()
            return True
        return False


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/livros', methods=['GET'])
def obter_livros():
    livros = LivroRepository.get_all()
    return jsonify([LivroDTO.from_model(l).__dict__ for l in livros])


@app.route('/livros/<int:id>', methods=['GET'])
def obter_livro_por_id(id):
    livro = LivroRepository.get_by_id(id)
    if livro:
        return jsonify(LivroDTO.from_model(livro).__dict__)
    return jsonify({'erro': 'Livro não encontrado'}), 404

@app.route('/livros', methods=['POST'])
def incluir_novo_livro():
    data = request.get_json()
    if not data or 'titulo' not in data or 'autor' not in data:
        return jsonify({'erro': 'Dados inválidos, informe titulo e autor'}), 400

    livro = LivroRepository.add(data['titulo'], data['autor'])
    return jsonify(LivroDTO.from_model(livro).__dict__), 201


@app.route('/livros/<int:id>', methods=['PUT'])
def editar_livro_por_id(id):
    data = request.get_json()
    if not data:
        return jsonify({'erro': 'Dados inválidos'}), 400

    livro = LivroRepository.update(id, data.get('titulo'), data.get('autor'))
    if livro:
        return jsonify(LivroDTO.from_model(livro).__dict__)
    return jsonify({'erro': 'Livro não encontrado'}), 404


@app.route('/livros/<int:id>', methods=['DELETE'])
def deletar_livro(id):
    if LivroRepository.delete(id):
        return jsonify({'mensagem': f'Livro {id} removido com sucesso!'})
    return jsonify({'erro': 'Livro não encontrado'}), 404



if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(port=5000, host='localhost', debug=True)

