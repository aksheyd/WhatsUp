# What's Up
> Learn your local laws through interactive engagement!

WhatsUp is a web application that makes local ordinances and laws accessible and interactive for community members. Created as part of the Data Driven Hackathon at the University of Michigan, Ann Arbor on 3/22/25.

## 🌟 Features

- **Interactive Law Learning**: Engage with local ordinances through AI-generated questions
- **Community Insights**: See how others in your area feel about specific laws
- **Source Transparency**: Direct links to original ordinance texts
- **Geographic Coverage**: Extensive database of state and county-level regulations

## 🏗 Technical Architecture

### Backend Infrastructure
- **Framework**: Django with Gunicorn
- **Deployment**: Fly.io with horizontal and vertical scaling
  - 3 machine/volume replicas for redundancy
  - RAM-based horizontal scaling
  - Fly.io load balancer for traffic distribution
  - LiteFS for database redundancy

### Data Collection
- **Web Scraping Pipeline**: 
  - Built with Selenium and BeautifulSoup4
  - Targets Municode library for comprehensive legal data
  - Collected state and county-level ordinances
  - *(Note: Full ordinance dataset available locally, production deployment pending due to size constraints)*

### AI Integration
- LLM-powered interaction system:
  - Generates relevant questions from ordinance texts
  - Links questions to source material
  - Tracks community response data

### Database
- Optimized for vote tracking and user interaction storage
- Managed by Fly.io with redundancy through LiteFS

## 🚀 Future Improvements

- [ ] Deploy full ordinance dataset
- [ ] Enhanced frontend user interface
- [ ] Additional community engagement features


## 🤝 Acknowledgments

- University of Michigan, Ann Arbor for hosting the Data Driven Hackathon
- Municode Library for being a comprehensive source of legal data

---