# 💸 Data Finance Hub: Pipeline ELT End-to-End

Projeto feito para o acompanhamento automatizado do câmbio. Este projeto utiliza uma abordagem Data Lakehouse para ingerir, armazenar e estruturar dados históricos do Dólar, permitindo o monitoramento de volatilidade e variações de preço através de um fluxo ELT robusto.

## 🏗 Arquitetura do Projeto

O pipeline segue o fluxo ELT (Extract, Load, Transform) orientado a eventos:
- **Ingestão (Low-Code)**: O n8n consulta uma API pública de cotações financeiras e deposita os dados brutos (JSON) no Data Lake.
- **Data Lake (Storage)**: O MinIO atua como Object Storage (compatível com AWS S3), armazenando os arquivos na camada Raw.
- **Orquestração**: O Apache Airflow utiliza um S3KeySensor para detectar a chegada de novos arquivos no bucket.
- **Processamento & Carga**: Uma DAG em Python processa o JSON (tratando listas/dicionários), valida os dados e insere as informações estruturadas no Data Warehouse.
- Data **Warehouse**: O PostgreSQL armazena os dados finais prontos para análise.

## 🛠 Tech Stack

- **Orquestração**: Apache Airflow 2.10.3 (Arquitetura Celery com Redis).
- **Ingestão/Automação**: n8n.
- **Object Storage**: MinIO (Para simular AWS S3).
- **Banco de Dados**: PostgreSQL 13.
- **Infraestrutura**: Docker & Docker Compose.

## 🚀 Como Executar

### 1. Pré-requisitos

Certifique-se de ter instalado:
- Docker Desktop & Docker Compose
- Git

### 2. Instalação

- Clone o repositório e configure as permissões de usuário:
```bash
    git clone https://github.com/enzortorres/data-finance-hub.git
    cd data-finance-hub

    # Linux/Mac (Configura permissão do usuário Airflow)
    echo "AIRFLOW_UID=$(id -u)" > .env

    # Windows PowerShell (Configura permissão padrão)
    echo "AIRFLOW_UID=50000" > .env
```

- Suba o ambiente:
```bash
    docker compose up -d
```
- Aguarde alguns minutos na primeira execução para que o Airflow realize as migrações do banco.

## ⚙️ Configuração (Pós-Instalação)

### 1. Acesso às Interfaces

|Serviço|URL|Usuário|Senha|
|:--|:--|:--|:--|
|Airflow|http://localhost:8080|admin|admin|
|MinIO|http://localhost:9001|minioadmin|minioadmin|
|n8n|http://localhost:5678|admin|admin|

### 2. Configurar Bucket (MinIO)

1. Acesse o MinIO (localhost:9001).
2. Crie um bucket chamado: ```raw-data```.

### 3. Configurar Conexões no Airflow

- No menu Admin > Connections, crie/edite as seguintes conexões:

1. Conexão Postgres (```postgres_dw```)
- **Conn Type**: ```Postgres```
- **Host**: ```postgres```
- **Schema**: ```airflow```
- **Login**: ```airflow```
- **Password**: ```airflow```
- **Port**: ```5432```

2. Conexão MinIO (```minio_conn```)
- **Conn Type**: ```Amazon Web Services```
- **AWS Access Key ID**: ```minioadmin```
- **AWS Secret Access Key**: ```minioadmin```
- **Extra**:
```json
    {
        "endpoint_url": "http://minio:9000"
    }
```
### 4. Configurar o workflow (```n8n```)

#### Preparação

- Acesse o n8n: http://localhost:5678
- **Usuário**: admin
- **Senha**: admin
- Clique em "Add Workflow".

#### Passo 1: O Gatilho (Schedule Trigger) define a periodicidade da ingestão.

Adicione o nó Schedule Trigger.

- **Trigger Interval**: ```Hours```
- **Hours Between Triggers**: ```1``` (ou o intervalo que preferir para testes).

#### Passo 2: Buscar Dados (HTTP Request)

- Adicione o nó HTTP Request.
- **Method**: ```GET```
- **URL**: ```https://economia.awesomeapi.com.br/last/USD-BRL```
- **Authentication**: ```None```
- Clique em Execute Node para garantir que o JSON chegou.

ex: 
```json
    {
        "USDBRL": {...}
    }
```

#### Passo 3: Criar o Arquivo (Convert to File).

- Adicione o nó Convert to File.
- **Operation**: ```Convert to JSON```
- **Mode**: ```All items to One File```
- **Put Output File in Field**: ```data```

#### Passo 4: Configurar Credencial MinIO
Se ainda não configurou:

- Vá em ```Credentials``` > ```Add Credential.```
- Escolha ```S3```.
- **Region**: ```us-east-1.```
- **Access Key ID**: ```minioadmin```
- **Secret Access Key**: ```minioadmin```
- **Endpoint**: ```http://minio:9000```
- **Force Path Style**: ative ON (Essencial).


#### Passo 5: Enviar para o Lake (S3 Node)
O passo final de carga.

Adicione o nó **S3** (o genérico/nativo).

- **Credential**: Selecione a credencial criada acima.
- **Operation**: ```Upload```
- **Bucket Name**: ```raw-data```

Para evitar problemas futuros com Windows por causa de espaços e dois pontos:

- **File Name**: Clique na engrenagem (Expression) e insira: ```cotacao-{{ $('HTTP Request').item.json.USDBRL.create_date.replace(' ', '_').replace(':', '-') }}.json```

Isso transforma ```2025-12-11 16:30:00``` em ```2025-12-11_16-30-00```.
- **Input Binary Field**: Garanta que está escrito ```data``` (ou o mesmo nome que você definiu no Passo 3).

### 📥Ou você pode importar o Workflow no n8n

1. Clique na seta abaixo para expandir o código.
2. Clique no ícone de **Copiar** (📋) que aparece no canto superior direito do código.
3. No n8n, pressione `Ctrl+V` (ou `Cmd+V`) na tela do editor.

<details>
  <summary><strong>📋 Clique aqui para ver o JSON do Workflow</strong></summary>

```json
    {
    "nodes": [
        {
        "parameters": {
            "rule": {
            "interval": [
                {
                "field": "hours"
                }
            ]
            }
        },
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.3,
        "position": [
            0,
            0
        ],
        "id": "9f0b3c56-6ca9-48c4-be72-e447e6ce178e",
        "name": "Schedule Trigger"
        },
        {
        "parameters": {
            "url": "https://economia.awesomeapi.com.br/last/USD-BRL",
            "options": {
            "response": {
                "response": {
                "responseFormat": "json"
                }
            }
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.3,
        "position": [
            208,
            0
        ],
        "id": "3f5e214c-decc-4910-9331-54649a15a180",
        "name": "HTTP Request"
        },
        {
        "parameters": {
            "operation": "upload",
            "bucketName": "raw-data",
            "fileName": "=cotacao-{{ $('HTTP Request').item.json.USDBRL.create_date.replace(' ', '_').replaceAll(':', '-') }}.json",
            "additionalFields": {}
        },
        "type": "n8n-nodes-base.s3",
        "typeVersion": 1,
        "position": [
            624,
            0
        ],
        "id": "e294f352-14ed-4a47-9d6c-4d13b9f60d3d",
        "name": "Upload a file",
        "credentials": {
            "s3": {
            "id": "ynRzp1T2055MQckQ",
            "name": "S3 account"
            }
        }
        },
        {
        "parameters": {
            "operation": "toJson",
            "options": {}
        },
        "type": "n8n-nodes-base.convertToFile",
        "typeVersion": 1.1,
        "position": [
            416,
            0
        ],
        "id": "09460834-e0a6-4493-a20e-c3472f549368",
        "name": "Convert to File"
        }
    ],
    "connections": {
        "Schedule Trigger": {
        "main": [
            [
            {
                "node": "HTTP Request",
                "type": "main",
                "index": 0
            }
            ]
        ]
        },
        "HTTP Request": {
        "main": [
            [
            {
                "node": "Convert to File",
                "type": "main",
                "index": 0
            }
            ]
        ]
        },
        "Convert to File": {
        "main": [
            [
            {
                "node": "Upload a file",
                "type": "main",
                "index": 0
            }
            ]
        ]
        }
    },
    "pinData": {},
    "meta": {
        "templateCredsSetupCompleted": true,
        "instanceId": "6271dbfb12293172553a17d793f5476298b06e742635a6df2e07990c24336f6a"
    }
    }
```
</details>

## 🧪 Testando o Pipeline

1.  No **n8n**, execute o workflow manualmente.
2.  Verifique no **MinIO** se o arquivo JSON apareceu no bucket `raw-data`.
3.  No **Airflow**, a DAG `data_etl_dolar` deve sair do estado de espera do sensor e processar o arquivo.
4.  Conecte-se ao banco via **DBeaver** (ou outro client SQL) para validar os dados:

    * **Host:** `localhost`
    * **Port:** `5432`
    * **Database:** `airflow`
    * **Username:** `airflow`
    * **Password:** `airflow`

    Execute a query:

```sql
    SELECT * FROM cotacao_dolar;
```