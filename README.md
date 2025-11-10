
# ElasticPy

**A lightweight, modular, and developer-friendly Python integration layer for Elasticsearch**

ElasticPy simplifies indexing, searching, and syncing data between your Python applications and Elasticsearch clusters with clean abstractions, async support, and built-in query helpers.
​

## Features

- **Clean Abstractions** - Intuitive Python API for Elasticsearch operations
- **Async Support** - Built-in asynchronous operations for high-performance applications
- **Query Helpers** - Pre-built utilities for common search patterns and queries
- **Modular Design** - Use only what you need with a flexible, pluggable architecture
- **Easy Indexing** - Streamlined methods for bulk and single document operations
- **Sync Operations** - Efficient data synchronization between your application and Elasticsearch
## Prerequisites

- Python 3.7+
- Elasticsearch 7.x or 8.x
- `uv` package manager
- `just` command runner (optional, for task automation)
## Installation

### 1. Install uv (if not already installed)

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation:**

```bash
uv --version
```

### 2. Clone and Setup

```bash
git clone https://github.com/Motssembillahmahin/elasticpy.git
cd elasticpy
```

### 3. Install Dependencies

```bash
uv sync
```

This command will automatically:
- Detect or download the appropriate Python version
- Create a virtual environment in `.venv`
- Install all project dependencies from `pyproject.toml`
- Generate/update the `uv.lock` lockfile

### 4. Activate Virtual Environment (Optional)

**Linux/macOS**
```bash
.venv\bin\activate
```
**Windows**
```bash
.venv\Scripts\activate
```

### Configure Environment Variables

Create a `.env` file in the project root:

ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_PASSWORD=your_password
ELASTICSEARCH_TIMEOUT=30
ELASTICSEARCH_MAX_RETRIES=3
DATABASE_URL=postgresql://user:password@localhost/dbname


### 5. Start Elasticsearch

Make sure Elasticsearch is running:

### Active Elasticsearch
```bash
sudo systemctl enable elasticsearch.service # active elasticsearch
sudo systemctl status elasticsearch.service # check status
```
### Check Elasticsearch active
```
curl -X GET http://localhost:9200
```

### Active Kibana
```bash
sudo systemctl enable elasticsearch.Kibana # active Kibana
sudo systemctl status elasticsearch.kiabana # check status
```

### Check kibana active
```
curl -X GET http://localhost:5601
```


### 6. Run the Application

**Using just**
```bash
just run
```

The API will be available at `http://localhost:8000`

## Quick Start


###  Check Elasticsearch Health

```bash
curl http://localhost:8000/admin/elasticsearch/health
```

**Response:**
```json
{
  "status": "green",
  "cluster_name": "elasticsearch",
  "number_of_nodes": 1,
  "active_shards": 5,
  "product_count": 1250
}
```


## Deployment

### SSL Certificate Warnings

If you see SSL warnings, they're suppressed in development mode:



```python
client =  AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            basic_auth=("elastic", settings.ELASTICSEARCH_PASSWORD),
            verify_certs=False,  # Disable cert verification for development
            ssl_show_warn=False,  # Suppress SSL warnings
            request_timeout=settings.ELASTICSEARCH_TIMEOUT,
            max_retries=settings.ELASTICSEARCH_MAX_RETRIES,
            retry_on_timeout=True,
            )
```

For production, use proper certificates:

```python
client = AsyncElasticsearch(
            verify_certs=True,
            ca_certs="/path/to/ca.crt"
            )
```

## API Documentation

Once the application is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Performance Tips

1. **Batch Size**: Adjust batch size based on document size and available memory
2. **Shards**: Use 3-5 shards for most use cases, more for very large datasets
3. **Replicas**: Use 1-2 replicas for redundancy (0 for development)
4. **Connection Pooling**: The singleton client pattern ensures efficient connection reuse
5. **Background Tasks**: Use FastAPI BackgroundTasks for long-running operations

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Install dependencies: `uv sync`
4. Make changes and test: `uv run pytest`
5. Format code: `just pre-commit .`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request


## Acknowledgments

- Built on [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- Powered by [Elasticsearch](https://www.elastic.co/) - Distributed search and analytics
- Package management by [uv](https://github.com/astral-sh/uv) - Extremely fast Python package manager

## Support

- **Issues**: [GitHub Issues](https://github.com/Motssembillahmahin/elasticpy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Motssembillahmahin/elasticpy/discussions)

---

**Made with ❤️ for the Python, FastAPI, and Elasticsearch community**
