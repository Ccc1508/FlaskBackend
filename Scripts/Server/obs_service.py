import os

from obs import ObsClient, PutObjectHeader

from config import Config


def upload_to_obs(file_path):
    obs_client = ObsClient(
        access_key_id=Config.OBS_AK,
        secret_access_key = Config.OBS_SK,
        server = Config.OBS_SERVER
        )

    # 设置目标路径
    object_name = os.path.basename(file_path)

    # 上传文件到OBS
    response = obs_client.putObject(
        bucketName=Config.OBS_BUCKET_NAME,
        objectKey=object_name,
        file_path=file_path,
        headers=PutObjectHeader()
    )

    if response.status < 300:
        # 返回文件的URL地址
        return f"{Config.OBS_SERVER}/{Config.OBS_BUCKET_NAME}/{object_name}"
    else:
        raise Exception(f"Failed to upload file to OBS: {response.errorMessage}")
