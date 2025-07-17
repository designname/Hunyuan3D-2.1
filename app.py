# app.py
import os
import uuid
import argparse
from flask import Flask, request, jsonify
from google.cloud import storage

# Импортируем ваш оригинальный demo.py
# Убедитесь, что demo.py находится в том же каталоге или доступен в PYTHONPATH
import demo 

app = Flask(__name__)

# Настройте имя вашего GCS бакета, куда будут сохраняться сгенерированные модели
# ЗАМЕНИТЕ 'YOUR_GCS_BUCKET_NAME' НА ИМЯ ВАШЕГО БАКЕТА
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'your-hunyuan3d-output-bucket') 
# Рекомендуется передавать имя бакета через переменную окружения Cloud Run

@app.route('/generate-3d', methods=['POST'])
def generate_3d_model():
    """
    Принимает POST-запрос с параметрами для генерации 3D-модели
    и сохраняет результат в Google Cloud Storage.
    """
    try:
        # Получаем параметры из JSON-тела запроса
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        prompt = data.get('prompt', 'a cute dog') # Текстовый запрос
        seed = int(data.get('seed', 42)) # Seed для воспроизводимости
        resolution = int(data.get('resolution', 256)) # Разрешение
        guidance_scale = float(data.get('guidance_scale', 7.5))
        num_inference_steps = int(data.get('num_inference_steps', 50))

        # Создаем временный путь для сохранения выходного файла в контейнере
        # Имя файла будет уникальным, чтобы избежать конфликтов
        unique_filename = f"model_{uuid.uuid4()}.glb" # Или .obj, в зависимости от demo.py
        temp_output_path = os.path.join("/tmp", unique_filename) 
        # /tmp - это рекомендуемое место для временных файлов в Cloud Run

        # Создаем объект Namespace для передачи аргументов в demo.main()
        # demo.py ожидает аргументы как объект argparse.Namespace
        args = argparse.Namespace(
            prompt=prompt,
            output_path=temp_output_path,
            seed=seed,
            resolution=resolution,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps
            # Добавьте сюда любые другие аргументы, которые ожидает ваш demo.py
            # и которые вы хотите передавать через API
        )

        app.logger.info(f"Starting 3D generation for prompt: '{prompt}'")
        app.logger.info(f"Output will be saved to temporary path: {temp_output_path}")

        # Вызываем основную функцию из demo.py
        # Убедитесь, что demo.main(args) действительно запускает генерацию
        # и сохраняет файл по args.output_path
        demo.main(args) 

        app.logger.info(f"3D generation completed. Uploading {temp_output_path} to GCS bucket: {GCS_BUCKET_NAME}")

        # Загружаем сгенерированный файл в Google Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(unique_filename) # Имя файла в GCS

        blob.upload_from_filename(temp_output_path)

        # Удаляем временный файл после загрузки
        os.remove(temp_output_path)

        gcs_public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{unique_filename}"
        app.logger.info(f"File uploaded to GCS: {gcs_public_url}")

        return jsonify({
            "status": "success",
            "message": "3D model generated and uploaded to GCS",
            "gcs_url": gcs_public_url,
            "prompt": prompt
        }), 200

    except Exception as e:
        app.logger.error(f"Error during 3D generation: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Запускаем Flask-приложение
# Cloud Run ожидает, что ваше приложение будет слушать на порту, 
# указанном в переменной окружения PORT (по умолчанию 8080).
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)