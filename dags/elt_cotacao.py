from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import json

BUCKET_NAME = 'raw-data'
AWS_CONN_ID = 'minio_conn'
DB_CONN_ID = 'postgres_dw'

def process_data_and_load():
    s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)
    
    keys = s3_hook.list_keys(bucket_name=BUCKET_NAME)
    
    if not keys:
        print("Nenhum arquivo encontrado.")
        return

    last_key = keys[-1]
    print(f"Processando arquivo: {last_key}")
    
    file_content = s3_hook.read_key(last_key, bucket_name=BUCKET_NAME)
    json_data = json.loads(file_content)
    
    if isinstance(json_data, list):
        if len(json_data) > 0:
            json_data = json_data[0]
        else:
            print("O arquivo JSON contém uma lista vazia.")
            return
    
    cotacao = json_data.get('USDBRL', {})
    valor_compra = cotacao.get('bid')
    data_hora = cotacao.get('create_date')
    
    if not valor_compra:
        print(f"Conteúdo recebido: {json_data}")
        raise ValueError("Dados inválidos")

    print(f"Dólar cotado a R$ {valor_compra} em {data_hora}")

    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)
    
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS cotacao_dolar (
            id SERIAL PRIMARY KEY,
            valor DECIMAL(10, 4),
            data_referencia TIMESTAMP,
            data_ingestao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    pg_hook.run(create_table_sql)
    
    insert_sql = """
        INSERT INTO cotacao_dolar (valor, data_referencia)
        VALUES (%s, %s);
    """
    pg_hook.run(insert_sql, parameters=(valor_compra, data_hora))
        
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'data_elt_dolar',
    default_args=default_args,
    schedule_interval='10 * * * *', # roda toda hora no minuto 10.
    catchup=False
) as dag:

    # sensor: fica esperando aparecer qualquer arquivo .json no bucket
    wait_for_file = S3KeySensor(
        task_id='wait_for_s3_file',
        bucket_name=BUCKET_NAME,
        bucket_key='*.json', # para qualquer json
        wildcard_match=True,
        aws_conn_id=AWS_CONN_ID,
        timeout=18 * 60 * 60, # time out após 18h
        poke_interval=60, # checa a cada 60s
    )

    process_and_load = PythonOperator(
        task_id='process_json_to_postgres',
        python_callable=process_data_and_load,
        provide_context=True
    )

    wait_for_file >> process_and_load