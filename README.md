\# iDrive e2 Prometheus Exporter



Monitor your iDrive e2 S3 storage with Prometheus and Grafana.



\## Features

\- 📊 Real-time storage metrics

\- 🏥 Health monitoring

\- ⚡ Performance tracking

\- 📈 Beautiful Grafana dashboard



\## Quick Start



\### Docker Compose

```bash

docker-compose up -d

```



\### Environment Variables

\- `ENDPOINT\_URL` - iDrive e2 endpoint

\- `REGION\_NAME` - Region (default: us-east-1)

\- `ACCESS\_KEY` - Your access key

\- `SECRET\_KEY` - Your secret key

\- `BUCKETS` - Comma-separated bucket names

\- `SCRAPE\_INTERVAL` - Scrape interval in seconds (default: 300)



\## Metrics

\- `idrive\_bucket\_size\_bytes` - Bucket size

\- `idrive\_bucket\_object\_count` - Object count

\- `idrive\_bucket\_healthy` - Health status

\- `idrive\_scrape\_duration\_seconds` - Scrape latency



\## Endpoints

\- `:8000/metrics` - Prometheus metrics

\- `:8001/health` - Health check (JSON)



\## Grafana Dashboard

Import from `grafana/dashboards/idrive-e2-dashboard.json`



\## Screenshots

\[Add screenshots here]



\## License

MIT

