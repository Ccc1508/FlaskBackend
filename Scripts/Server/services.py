from sqlalchemy import func

from models import Batch, DefectiveItem, DefectDetail, db


# 序列化 Batch 信息
def serialize_batch(batch):
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
def get_batch_summary():
    total_items = db.session.query(func.sum(Batch.total_items)).scalar()
    defective_items = db.session.query(func.sum(Batch.defective_items)).scalar()

    defective_rate = defective_items / total_items if total_items else 0.0
    return {
        'total_items': total_items,
        'defective_items': defective_items,
        'defective_rate': defective_rate
    }


# 获取指定批次信息
def get_single_batch_summary(batch_id):
    batch = Batch.query.get(batch_id)
    if batch is None:
        return None

    total_items = batch.total_items
    defective_items = batch.defective_items
    defective_rate = defective_items / total_items if total_items else 0.0

    return {
        'batch_id': batch_id,
        'total_items': total_items,
        'defective_items': defective_items,
        'defective_rate': defective_rate,
    }


# 单个批次的缺陷统计
def single_statistics(batch_id):
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

    mouse_bite, open_circuit, short, spur, spurious_copper = total_defects
    total_defects_count = sum([mouse_bite, open_circuit, short, spur, spurious_copper]) or 1

    return {
        'mouse_bite': {'count': mouse_bite or 0, 'probability': (mouse_bite or 0) / total_defects_count},
        'open_circuit': {'count': open_circuit or 0, 'probability': (open_circuit or 0) / total_defects_count},
        'short': {'count': short or 0, 'probability': (short or 0) / total_defects_count},
        'spur': {'count': spur or 0, 'probability': (spur or 0) / total_defects_count},
        'spurious_copper': {'count': spurious_copper or 0, 'probability': (spurious_copper or 0) / total_defects_count}
    }


# 统计缺陷数据
def statistics():
    total_defects = (
        db.session.query(
            func.sum(DefectDetail.Mouse_bite),
            func.sum(DefectDetail.Open_circuit),
            func.sum(DefectDetail.Short),
            func.sum(DefectDetail.Spur),
            func.sum(DefectDetail.Spurious_copper)
        ).one()
    )

    mouse_bite_total, open_circuit_total, short_total, spur_total, spurious_copper_total = total_defects
    total_defects_sum = sum(total_defects) or 1

    probabilities = {
        'mouse_bite_probability': (mouse_bite_total / total_defects_sum) * 100,
        'open_circuit_probability': (open_circuit_total / total_defects_sum) * 100,
        'short_probability': (short_total / total_defects_sum) * 100,
        'spur_probability': (spur_total / total_defects_sum) * 100,
        'spurious_copper_probability': (spurious_copper_total / total_defects_sum) * 100,
    }

    return {
        'mouse_bite_total': mouse_bite_total,
        'open_circuit_total': open_circuit_total,
        'short_total': short_total,
        'spur_total': spur_total,
        'spurious_copper_total': spurious_copper_total,
        **probabilities
    }
