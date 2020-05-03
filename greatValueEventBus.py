import json
import boto3

def lambda_handler(event, context):
    print(event)
    print("\n\n")
    file = event['Records'][0]['s3']['object']['key']
    print(file)
    client = boto3.client('ecs')

    cluster = 'repiece-clustermaster'
    taskDefinition = 'repiece-task-master'
    overrides = {'containerOverrides':[{
        'name':'main',
        'environment':[
            {'name':'file', 'value':file}]}]}

    subnets = 'subnet-614c513c'
    networkConfig = {'awsvpcConfiguration':{'subnets':subnets, 'assignPublicIp':'DISABLED'}
    }
    


    response = client.run_task(
        cluster=cluster,
        launchType='FARGATE',
        taskDefinition=taskDefinition,
        overrides=overrides,
        networkConfiguration=networkConfig
    )
    print(response)
    