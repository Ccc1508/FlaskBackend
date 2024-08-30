from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# 批次模型
class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_items = db.Column(db.Integer)
    defective_items = db.Column(db.Integer)
    defective_items_list = db.relationship('DefectiveItem', backref='batch', lazy=True)


# 缺陷物体模型
class DefectiveItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    quantity = db.Column(db.Integer)
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    defects = db.relationship('DefectDetail', backref='defective_item', uselist=False)


# 缺陷详情模型
class DefectDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(255))
    Mouse_bite = db.Column(db.Integer)
    Open_circuit = db.Column(db.Integer)
    Short = db.Column(db.Integer)
    Spur = db.Column(db.Integer)
    Spurious_copper = db.Column(db.Integer)
    defective_item_id = db.Column(db.Integer, db.ForeignKey('defective_item.id'))
    defect_types = db.relationship('DefectType', backref='defect_detail', lazy=True)


# 缺陷类型模型
class DefectType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    defect_detail_id = db.Column(db.Integer, db.ForeignKey('defect_detail.id'))
    defect_type = db.Column(db.String(50))
    detection_boxes = db.Column(db.String(100))
    detection_scores = db.Column(db.Numeric(5, 2))
