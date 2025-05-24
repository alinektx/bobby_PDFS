from flask import Flask, request, render_template, redirect, url_for, send_from_directory, send_file
import os
import shutil
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from werkzeug.utils import secure_filename
import zipfile
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['RESIZE_FOLDER'] = 'recortes'

# Caminho para o Poppler
poppler_path = r'C:\Release-24.08.0-0\poppler-24.08.0\Library\bin'  # Ajuste este caminho conforme necessário

# Configurar o caminho para o executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Ajuste este caminho conforme necessário

# Criar pastas se não existirem
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESIZE_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        return redirect(request.url)
    files = request.files.getlist('files')
    if not files:
        return redirect(request.url)
    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
    process_files()
    return redirect(url_for('results'))

@app.route('/results')
def results():
    com_codigo = os.listdir(os.path.join(app.config['OUTPUT_FOLDER'], 'com_codigo'))
    sem_codigo = os.listdir(os.path.join(app.config['OUTPUT_FOLDER'], 'sem_codigo'))
    return render_template('results.html', com_codigo=com_codigo, sem_codigo=sem_codigo)

@app.route('/download/<path:folder>')
def download_files(folder):
    folder_path = os.path.join(app.config['OUTPUT_FOLDER'], folder)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            zip_file.write(file_path, file_name)
    zip_buffer.seek(0)
    return send_file(zip_buffer, download_name=f'{folder}.zip', as_attachment=True)

def process_files():
    pasta_pdfs = app.config['UPLOAD_FOLDER']
    pasta_com_codigo = os.path.join(app.config['OUTPUT_FOLDER'], 'com_codigo')
    pasta_sem_codigo = os.path.join(app.config['OUTPUT_FOLDER'], 'sem_codigo')
    pasta_recortes = os.path.join(app.config['RESIZE_FOLDER'])  # Diretório para salvar as imagens recortadas

    # Criar pastas se não existirem
    os.makedirs(pasta_com_codigo, exist_ok=True)
    os.makedirs(pasta_sem_codigo, exist_ok=True)
    os.makedirs(pasta_recortes, exist_ok=True)  # Criar o diretório para os recortes

    # Variável de contagem global de páginas
    contador_global = 1

    # Ordena os arquivos para manter a sequência
    arquivos_pdf = sorted([f for f in os.listdir(pasta_pdfs) if f.endswith('.pdf')])

    for i, arquivo in enumerate(arquivos_pdf, start=1):
        caminho_pdf = os.path.join(pasta_pdfs, arquivo)

        print(f"Processando arquivo: {arquivo}")

        try:
            # Converte a primeira página do PDF para imagem com caminho do Poppler
            imagens = convert_from_path(caminho_pdf, first_page=1, last_page=1, poppler_path=poppler_path)
            imagem = imagens[0]
            print(f"Imagem convertida com sucesso: {arquivo}")
        except Exception as e:
            print(f"Erro ao converter {arquivo}: {e}")
            continue

        # Corta o canto superior direito da imagem
        largura, altura = imagem.size
        area_codigo = imagem.crop((
            largura * 0.70,  # canto direito (10% da largura)
            0,
            largura,
            altura * 0.12    # parte de cima (10% da altura)
        ))

        # Salvar a imagem da área recortada para verificação
        caminho_area_codigo = os.path.join(pasta_recortes, f"area_codigo_{i:02d}.png")
        area_codigo.save(caminho_area_codigo)
        print(f"Área recortada salva em: {caminho_area_codigo}")

        # OCR
        texto = pytesseract.image_to_string(area_codigo)
        print(f"Texto extraído de {arquivo}: {texto.strip()}")

        # Define pasta de destino
        if texto.strip():
            destino_pasta = pasta_com_codigo
            print(f"Arquivo {arquivo} tem código.")
        else:
            destino_pasta = pasta_sem_codigo
            print(f"Arquivo {arquivo} não tem código.")

        # Cria novo nome do arquivo
        nome_arquivo = f"{i:02d}_PAGINA_{contador_global:04d}.pdf"
        destino = os.path.join(destino_pasta, nome_arquivo)

        # Move e renomeia o arquivo
        try:
            shutil.move(caminho_pdf, destino)
            print(f'{arquivo} → {nome_arquivo} ({ "com código" if texto.strip() else "sem código" })')
        except Exception as e:
            print(f"Erro ao mover {arquivo} para {destino}: {e}")

        # Incrementa contador global
        contador_global += 1

    print("Processamento concluído.")

if __name__ == '__main__':
    app.run(debug=True, port=5000)