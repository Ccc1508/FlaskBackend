from flask import Flask, jsonify, request

from config import Config
from infer_service import infer_image
from models import db
from obs_service import upload_to_obs
from services import get_batch_summary, get_single_batch_summary, single_statistics, statistics

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI
db.init_app(app)


# 获取批次汇总信息
@app.route('/batches/summary', methods=['GET'])
def batch_summary():
    summary = get_batch_summary()
    return jsonify(summary)


# 获取单个批次汇总信息
@app.route('/batches/<int:batch_id>/summary', methods=['GET'])
def single_batch_summary(batch_id):
    summary = get_single_batch_summary(batch_id)
    if summary is None:
        return jsonify({'error': 'Batch not found'}), 404
    return jsonify(summary)


# 获取单个批次的缺陷统计
@app.route('/batches/<int:batch_id>/statistics', methods=['GET'])
def batch_statistics(batch_id):
    stats = single_statistics(batch_id)
    if stats is None:
        return jsonify({'error': 'Batch not found'}), 404
    return jsonify(stats)


# 获取所有批次的缺陷统计
@app.route('/statistics', methods=['GET'])
def all_statistics():
    stats = statistics()
    return jsonify(stats)


# 上传图片并进行推理
@app.route('/infer', methods=['POST'])
def infer():
    file = request.files['file']
    file_path = f"/tmp/{file.filename}"
    file.save(file_path)

    try:
        # 上传到OBS
        image_url = upload_to_obs(file_path)

        # 执行推理
        result = infer_image(image_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
