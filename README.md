# job-digest

Resumo semanal de ofertas de emprego para Coimbra (raio ≤ 20 km) ou 100% remotas, filtradas por palavras-chave.

```bash
pip install -r requirements.txt
python3 job_digest.py --days 7      # gera digest.html, digest.txt e digest.json
```

- `job_digest.py`: itjobs.pt, net-empregos.com, filtros (palavras-chave, distância, remoto) e geração do resumo.
- `sources.py`: LinkedIn, landing.jobs, SAPO Emprego (precisa de Chrome com CDP em `localhost:29229`), Carga de Trabalhos,
  TecnoJobs, Teamlyzer, Bolsa da Ordem dos Engenheiros (Informática), NetEmprego, IEFP, BEP, Portal Emprego, Foundever e UC Apply.

O envio é feito pela automação semanal do Devin (Gmail), segunda-feira às 08:47 (Europe/Lisbon).
