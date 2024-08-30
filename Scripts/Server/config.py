class Config:
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://harmony:123456@101.43.96.132/harmonyos'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 华为云OBS服务配置
    OBS_AK = "RTHDGTQWOD7XI4VVXDU2"
    OBS_SK = "GsuwxkTy9EUxQWSgSxch65Dbk7Bovv1JY0aEhpzk"
    OBS_BUCKET_NAME = 'flask-pics'
    OBS_SERVER = 'https://obs.cn-southwest-2.myhuaweicloud.com'

    # 模型推理配置
    INFER_AK = "RTHDGTQWOD7XI4VVXDU2"
    INFER_SK = "GsuwxkTy9EUxQWSgSxch65Dbk7Bovv1JY0aEhpzk"
    INFER_URL = "https://infer-modelarts-cn-southwest-2.myhuaweicloud.com/v1/infers/2db1606a-62dc-46c5-81cd-d0781cf2bd37"
