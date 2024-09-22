import json
import os
from datetime import datetime

import requests
from flask import Flask
from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy
from obs import ObsClient, PutObjectHeader
from sqlalchemy import func
from werkzeug.utils import secure_filename

from apigw_sdk.apig_sdk import signer

app = Flask(__name__)
ak = "RTHDGTQWOD7XI4VVXDU2"
sk = "GsuwxkTy9EUxQWSgSxch65Dbk7Bovv1JY0aEhpzk"
url = "https://infer-modelarts-cn-southwest-2.myhuaweicloud.com/v1/infers/2db1606a-62dc-46c5-81cd-d0781cf2bd37"

ak1 = "PRQSIGRDLJTYWFOAO3L9"
sk1 = "r7tohXSSdKymmm86CxpDKmamJk9ERVTB1qbgxXte"
url1 = "https://infer-modelarts-cn-southwest-2.myhuaweicloud.com/v1/infers/fce819e1-e4bc-4fdf-9c52-e8faedd40b33"

# 配置数据库连接信息
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://harmony:123456@101.43.96.132/harmonyos'
db = SQLAlchemy(app)


# Batch Model (批次模型)
class Batch(db.Model):
    # 批次
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 时间戳
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # 总检测数
    total_items = db.Column(db.Integer)
    # 缺陷数
    defective_items = db.Column(db.Integer)
    # 关联的缺陷列表
    defective_items_list = db.relationship('DefectiveItem', backref='batch', lazy=True)


# DefectiveItem Model (缺陷物体模型)
class DefectiveItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 物品名称
    name = db.Column(db.String(80))
    # 数量
    quantity = db.Column(db.Integer)
    # 所属批次
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    # 缺陷详情
    defects = db.relationship('DefectDetail', backref='defective_item', uselist=False)


# DefectDetail Model (缺陷详情模型)
class DefectDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 图片URL
    image_url = db.Column(db.String(255))
    # 缺陷种类
    Mouse_bite = db.Column(db.Integer)
    Open_circuit = db.Column(db.Integer)
    Short = db.Column(db.Integer)
    Spur = db.Column(db.Integer)
    Spurious_copper = db.Column(db.Integer)
    # 所属缺陷物品id
    defective_item_id = db.Column(db.Integer, db.ForeignKey('defective_item.id'))
    # 关联的缺陷类型列表
    defect_types = db.relationship('DefectType', backref='defect_detail', lazy=True)


# DefectType Model (缺陷类型模型)
class DefectType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 所属缺陷详情id
    defect_detail_id = db.Column(db.Integer, db.ForeignKey('defect_detail.id'))
    # 缺陷名称
    defect_type = db.Column(db.String(50))  # 缺陷类型名称
    # 检测框坐标
    detection_boxes = db.Column(db.String(100))  # 用字符串存储坐标
    # 检测置信度
    detection_scores = db.Column(db.Numeric(5, 2))  # 精确度


# 若数据库未初始化，将此处注释去除，运行后，再次注释
# with app.app_context():
#     db.create_all()

# 序列化 Batch 信息
def SerializeBatch(batch):
    return {
        'id': batch.id,
        'timestamp': batch.timestamp.isoformat(),
        'total_items': batch.total_items,
        'defective_items': batch.defective_items,
        'defective_items_list': [
            {
                'name': item.name,
                'quantity': item.quantity,
                'defects': {
                    'image_url': item.defects.image_url if item.defects else None,
                    'Mouse_bite': item.defects.Mouse_bite if item.defects else 0,
                    'Open_circuit': item.defects.Open_circuit if item.defects else 0,
                    'Short': item.defects.Short if item.defects else 0,
                    'Spur': item.defects.Spur if item.defects else 0,
                    'Spurious_copper': item.defects.Spurious_copper if item.defects else 0,
                    'defect_types': [
                        {
                            'defect_type': defect_type.defect_type,
                            'detection_boxes': defect_type.detection_boxes,
                            'detection_scores': float(defect_type.detection_scores)
                        }
                        for defect_type in item.defects.defect_types
                    ] if item.defects else []
                }
            }
            for item in batch.defective_items_list
        ]
    }


# 获取批次汇总信息
def GetBatchSummary():
    total_items = db.session.query(func.sum(Batch.total_items)).scalar()
    defective_items = db.session.query(func.sum(Batch.defective_items)).scalar()

    # 计算缺陷率
    if total_items:
        defective_rate = defective_items / total_items
    else:
        defective_rate = 0.0
    return {
        'total_items': total_items,
        'defective_items': defective_items,
        'defective_rate': defective_rate
    }


# 获取指定批次信息
def GetSingleBatchSummary(batch_id):
    # 查询特定批次的信息
    batch = Batch.query.get(batch_id)

    if batch is None:
        return None

    # 计算总检测数
    total_items = batch.total_items

    # 计算缺陷数
    defective_items = batch.defective_items

    # 计算缺陷率
    if total_items:
        defective_rate = defective_items / total_items
    else:
        defective_rate = 0.0

    # 返回汇总信息
    return {
        'batch_id': batch_id,
        'total_items': total_items,
        'defective_items': defective_items,
        'defective_rate': defective_rate,
    }


def SingleStatistics(batch_id):
    # 查询指定批次的各种缺陷总数
    total_defects = (
        db.session.query(
            func.sum(DefectDetail.Mouse_bite).label('mouse_bite'),
            func.sum(DefectDetail.Open_circuit).label('open_circuit'),
            func.sum(DefectDetail.Short).label('short'),
            func.sum(DefectDetail.Spur).label('spur'),
            func.sum(DefectDetail.Spurious_copper).label('spurious_copper')
        )
        .join(DefectiveItem, DefectDetail.defective_item_id == DefectiveItem.id)
        .filter(DefectiveItem.batch_id == batch_id)
        .one_or_none()
    )

    if total_defects is None:
        return None

    # 解包结果
    mouse_bite, open_circuit, short, spur, spurious_copper = total_defects

    # 计算总缺陷数
    total_defects_count = sum([mouse_bite, open_circuit, short, spur, spurious_copper])

    if total_defects_count == 0:
        total_defects_count = 1

    # 计算每种缺陷的概率
    mouse_bite_prob = (mouse_bite or 0) / total_defects_count
    open_circuit_prob = (open_circuit or 0) / total_defects_count
    short_prob = (short or 0) / total_defects_count
    spur_prob = (spur or 0) / total_defects_count
    spurious_copper_prob = (spurious_copper or 0) / total_defects_count

    # 返回概率信息
    return {
        'mouse_bite': {'count': mouse_bite or 0, 'probability': mouse_bite_prob},
        'open_circuit': {'count': open_circuit or 0, 'probability': open_circuit_prob},
        'short': {'count': short or 0, 'probability': short_prob},
        'spur': {'count': spur or 0, 'probability': spur_prob},
        'spurious_copper': {'count': spurious_copper or 0, 'probability': spurious_copper_prob}
    }


# 统计缺陷数据
def Statistics():
    # 查询各种缺陷总数
    total_defects = (
        db.session.query(
            func.sum(DefectDetail.Mouse_bite),
            func.sum(DefectDetail.Open_circuit),
            func.sum(DefectDetail.Short),
            func.sum(DefectDetail.Spur),
            func.sum(DefectDetail.Spurious_copper)
        ).one()
    )

    # 解包
    mouse_bite_total, open_circuit_total, short_total, spur_total, spurious_copper_total = total_defects

    # 计算总数
    total_defects_sum = sum(total_defects)

    # 计算各类缺陷概率
    probabilities = {
        'mouse_bite_probability': (mouse_bite_total / total_defects_sum) * 100 if total_defects_sum else 0,
        'open_circuit_probability': (open_circuit_total / total_defects_sum) * 100 if total_defects_sum else 0,
        'short_probability': (short_total / total_defects_sum) * 100 if total_defects_sum else 0,
        'spur_probability': (spur_total / total_defects_sum) * 100 if total_defects_sum else 0,
        'spurious_copper_probability': (spurious_copper_total / total_defects_sum) * 100 if total_defects_sum else 0,
    }

    return {
        'mouse_bite_total': mouse_bite_total,
        'open_circuit_total': open_circuit_total,
        'short_total': short_total,
        'spur_total': spur_total,
        'spurious_copper_total': spurious_copper_total,
        **probabilities
    }


# 上传文件至华为云OBS服务
def UploadToObs(file_path):
    # 访问密钥
    ak = "RTHDGTQWOD7XI4VVXDU2"
    sk = "GsuwxkTy9EUxQWSgSxch65Dbk7Bovv1JY0aEhpzk"
    bucket_name = 'flask-pics'
    server = 'https://obs.cn-southwest-2.myhuaweicloud.com'
    object_key = os.path.basename(file_path)

    # 创建OBS客户端实例
    obs_client = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)

    try:
        headers = PutObjectHeader()
        headers.contentType = 'application/octet-stream'
        response = obs_client.putFile(bucketName=bucket_name, objectKey=object_key, file_path=file_path,
                                      headers=headers)

        # 删除本地临时文件
        os.remove(file_path)

        # 返回上传的URL
        return response.body.objectUrl
    except Exception as e:
        return e


# 调用模型进行缺陷检测推理
def Detect(file, ak, sk, url):
    method = 'POST'
    headers = {"x-sdk-content-sha256": "UNSIGNED-PAYLOAD"}
    request_det = signer.HttpRequest(method, url, headers)

    sig = signer.Signer()
    sig.Key = ak
    sig.Secret = sk
    sig.Sign(request_det)

    # 使用requests库发送文件
    files = {'images': file}
    resp = requests.request(request_det.method, request_det.scheme + "://" + request_det.host + request_det.uri,
                            headers=request_det.headers, files=files)

    if resp.status_code == 200:
        return resp.text
    else:
        return resp.status_code


# 处理检测结果并保存到数据库
def ProcessDetectionResults(file_path, batch_id):
    # 调用检测函数
    detection_result = Detect(open(file_path, 'rb'))

    # 如果返回状态码，则失败
    if isinstance(detection_result, int):
        print("Detection failed with status code", detection_result)
        return

    # 解析检测结果
    try:
        detection_json = json.loads(detection_result)
        # Debug.Log("检测结果")
        print(detection_json)
    except json.JSONDecodeError:
        print("Failed to parse JSON from detection result")
        return

    # 获取批次信息
    batch = Batch.query.get(batch_id)

    # 创建缺陷物品记录
    defective_items = DefectiveItem(
        name=file_path,
        quantity=1,
        batch_id=batch_id
    )
    db.session.add(defective_items)
    db.session.commit()

    # 上传文件到OBS并创建缺陷详情记录
    obs_object_url = UploadToObs(file_path)

    defect_detail = DefectDetail(
        image_url=obs_object_url,
        Mouse_bite=0,
        Open_circuit=0,
        Short=0,
        Spur=0,
        Spurious_copper=0,
        defective_item_id=defective_items.id
    )
    db.session.add(defect_detail)
    db.session.commit()

    # 创建缺陷类型记录并更新缺陷统计数据
    has_defects = False  # 缺陷标记
    defect_type_record_all = []
    for i, defect_type in enumerate(detection_json.get('detection_classes', [])):

        # 获取置信度分数
        detection_score = detection_json['detection_scores'][i]

        # 获取位置信息
        detection_boxes = detection_json['detection_boxes'][i]

        # 根据检测结果更新 DefectDetail 中的字段
        if defect_type == 'Mouse_bite':
            defect_detail.Mouse_bite += 1
        elif defect_type == 'Open_circuit':
            defect_detail.Open_circuit += 1
        elif defect_type == 'Short':
            defect_detail.Short += 1
        elif defect_type == 'Spur':
            defect_detail.Spur += 1
        elif defect_type == 'Spurious_copper':
            defect_detail.Spurious_copper += 1
        else:
            continue

        # 创建DefectType记录
        defect_type_record = DefectType(
            defect_type=defect_type,
            # 将列表转换为字符串存储
            detection_boxes=str(detection_boxes),
            detection_scores=detection_score,
            defect_detail_id=defect_detail.id
        )
        defect_type_record_all.append(defect_type_record)

        # 如果检测到缺陷，设置标记
        if detection_score > 0:
            has_defects = True

    # 如果检测到缺陷，保存记录并更新批次的缺陷物品数量
    if has_defects:
        db.session.add_all(defect_type_record_all)
        batch.defective_items += 1

    db.session.commit()


# API: 文件上传并检测(不存入数据库)
@app.route('/UploadPic/', methods=['POST'])
def UploadPic():
    files = request.files.getlist('file') if request.method == 'POST' else None

    if not files:
        return 'No files'

    # 初始化空列表存储检测结果
    results = []

    for file in files:
        # 对文件调用detect函数
        detection_result = Detect(file)
        results.append(detection_result)

    # 返回结果
    return jsonify(results)


# API: 文件上传并检测传入数据库
@app.route('/UploadPics', methods=['POST'])
def UploadPics():
    if request.method == 'POST':
        # 获取上传的文件列表
        files = request.files.getlist('file')

        if not files:
            return 'No Files'

        filenames = []

        # 创建新的批次
        new_batch = Batch(
            total_items=len(files),
            defective_items=0
        )
        db.session.add(new_batch)
        db.session.commit()

        for file in files:
            if file.filename == '':
                continue
            # 获取文件名
            filename = secure_filename(file.filename)
            # 存储
            directory = os.path.join('Assets', 'UploadAndDownloadPics')
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, filename)
            file.save(os.path.join('Assets/UploadAndDownloadPics', filename))
            filenames.append(filename)

            # 处理检测结果并保存到数据库
            ProcessDetectionResults(file_path, new_batch.id)  # 使用 new_batch.id

        if not filenames:
            return 'No Files'

        # 计算批次的缺陷率,并判断是否需要警报
        defective_rate = new_batch.defective_items / float(new_batch.defective_items) if new_batch.defective_items > 0 else 0
        if defective_rate > 0.3:
            return f"Batch{new_batch.id} : rate {defective_rate} : Unqualified"


@app.route('/PcbData/<int:batch_id>', methods=['GET'])
def GetSinglePcbData(batch_id):
    pcb_summary = GetSingleBatchSummary(batch_id)
    if pcb_summary is None:
        return jsonify({'error': 'No PCB data found'}), 404
    return jsonify(pcb_summary), 200


# API: 获取PCB数据汇总
@app.route('/PcbData', methods=['GET'])
def GetPcbData():
    pcb = GetBatchSummary()
    if pcb is None:
        return jsonify({'error': 'No PCB data found.'}), 404
    return jsonify(pcb), 200


@app.route('/Statistics/<int:batch_id>', methods=['GET'])
def GetSingleStatistics(batch_id):
    stats = SingleStatistics(batch_id)
    if stats is None:
        return jsonify({'error': 'No statistics data found'}), 404
    return jsonify(stats), 200


# API: 获取统计数据
@app.route('/Statistics', methods=['GET'])
def GetStatistics():
    stats = Statistics()
    if stats is None:
        return jsonify({'error': 'No statistics data found.'}), 404
    return jsonify(stats), 200


# API: 获取所有批次信息
@app.route('/batches', methods=['GET', 'POST'])
def GetBatches():
    batches = Batch.query.all()
    serialized_batches = [SerializeBatch(batch) for batch in batches]
    return jsonify(serialized_batches)


# API: 根据 batch_id 获取单个批次信息
@app.route('/batche/<int:batch_id>', methods=['GET', 'POST'])
def GetBatch(batch_id):
    batch = Batch.query.get(batch_id)
    return jsonify(SerializeBatch(batch))


# 查询最近5个批次的信息
@app.route('/last5batches', methods=['GET'])
def GetRecentBatches():
    # 查询最近 5 个批次，按照时间戳降序排序
    recent_batches = Batch.query.order_by(Batch.timestamp.desc()).limit(5).all()
    # 序列化批次数据
    serialized_batches = [SerializeBatch(batch) for batch in recent_batches]
    return jsonify(serialized_batches), 200


@app.route('/last_batch', methods=['GET'])
def GetLastBatch():
    # 按时间戳升序排列并获取最后一个批次
    last_batch = Batch.query.order_by(Batch.timestamp.desc()).first()

    if last_batch is None:
        return jsonify({'error': 'No batch data found'}), 404

    serialized_batch = SerializeBatch(last_batch)

    return jsonify(serialized_batch), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

# TODO ：切换ak&sk和url