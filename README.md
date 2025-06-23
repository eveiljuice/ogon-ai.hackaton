# AgentCore - AI Agent Marketplace

A comprehensive web application that serves as a marketplace for AI agents, built with Vue.js frontend and FastAPI backend. AgentCore provides users with access to specialized AI assistants for various tasks including creative writing, coding, research, business consulting, and data science.

**Video demonstration**: [Смотреть на Google Drive](https://drive.google.com/file/d/1X9Lx7OyTpHR0Qysc8DtTXwxW7wikjG1W/view?usp=drive_link)  
**Web-app AgentCore**: [agentcorebeta.replit.app](https://agentcorebeta.replit.app/)



## 🚀 Features

### Core Functionality
- **AI Agent Marketplace**: Browse and interact with 5 specialized AI agents
- **Real-time Chat**: WebSocket-powered chat interface with streaming responses
- **User Authentication**: Secure registration and login system
- **Premium Access**: Stripe payment integration for premium agents
- **Agent Management**: Complete CRUD operations for agents (admin only)

### User Experience
- **Responsive Design**: Mobile-friendly interface with dark theme
- **Voice Input**: Speech-to-text functionality for hands-free interaction
- **Favorites System**: Save and organize preferred agents
- **Chat History**: Persistent conversation storage and management
- **Dashboard**: Personal analytics and usage statistics
- **Prompt Enhancement**: AI-powered prompt optimization

### Administrative Features
- **Admin Panel**: Comprehensive management interface
- **User Management**: View, manage, and moderate user accounts
- **System Analytics**: Detailed usage statistics and metrics
- **Agent Analytics**: Performance tracking for each AI agent
- **Data Maintenance**: Automated cleanup and system health monitoring

## 🤖 Available AI Agents

### Free Agents
1. **Creative Writer** ✍️ - Specialized in creative writing, storytelling, and content creation
2. **Code Helper** 💻 - Programming assistant for debugging, code review, and technical documentation
3. **Research Assistant** 🔍 - Knowledge synthesis, fact-checking, and research support

### Premium Agents
1. **Business Advisor** 📊 - Strategic business consulting and market analysis ($29.99)
2. **Data Scientist** 📈 - Advanced data analysis, machine learning, and statistical modeling ($39.99)

## 🛠 Technology Stack

### Frontend
- **Vue.js 3** - Progressive JavaScript framework
- **Bootstrap 5** - CSS framework for responsive design
- **Font Awesome** - Icon library
- **WebSocket API** - Real-time communication

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **asyncpg** - Async PostgreSQL driver
- **OpenAI API** - AI model integration
- **Stripe API** - Payment processing
- **bcrypt** - Password hashing
- **JWT** - Authentication tokens

### Infrastructure
- **Uvicorn** - ASGI server
- **WebSocket** - Real-time messaging
- **File Upload** - Multi-format file handling

## 📦 Installation

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Node.js (for development tools)

### Environment Variables
Create a `.env` file or set the following environment variables:

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost/agencore

# API Keys
OPENAI_API_KEY=your_openai_api_key
STRIPE_SECRET_KEY=your_stripe_secret_key
VITE_STRIPE_PUBLIC_KEY=your_stripe_public_key

# Optional
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agencore
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the database**
   - Create a PostgreSQL database
   - Update the `DATABASE_URL` environment variable

4. **Initialize the database**
   ```bash
   python -c "import asyncio; from database import Database; asyncio.run(Database().init_database())"
   ```

5. **Start the application**
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## 🔧 Configuration

### Admin Access
- Create an account with email: `admin@agencore.com`
- This email automatically grants admin privileges
- Access admin panel via the "Admin Panel" button

### Payment Setup
1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe dashboard
3. Set the `STRIPE_SECRET_KEY` and `VITE_STRIPE_PUBLIC_KEY` environment variables

### AI Model Configuration
- The application uses OpenAI's GPT-4o model by default
- Anthropic Claude support is available but optional
- API keys are required for AI functionality

## 📁 Project Structure

```
agencore/
├── main.py                 # FastAPI application entry point
├── agents.py              # AI agent configurations
├── auth.py                # Authentication management
├── chat.py                # Chat and AI interaction logic
├── database.py            # Database operations
├── payments.py            # Stripe payment processing
├── admin.py               # Administrative functions
├── websocket_handler.py   # WebSocket connection management
├── static/
│   ├── index.html         # Main application template
│   ├── app.js            # Vue.js application logic
│   └── style.css         # Application styling
├── uploads/              # File upload directory
└── README.md            # This file
```

## 🎯 Usage

### For Users
1. **Registration**: Create an account using email and password
2. **Browse Agents**: Explore available AI agents on the homepage
3. **Free Agents**: Start chatting immediately with free agents
4. **Premium Agents**: Purchase access via Stripe payment
5. **Favorites**: Add frequently used agents to favorites
6. **Dashboard**: View your usage statistics and history

### For Administrators
1. **System Monitoring**: View overall system statistics
2. **User Management**: Monitor and manage user accounts
3. **Agent Analytics**: Track agent performance and usage
4. **Agent Management**: Create, edit, and manage AI agents
5. **Maintenance**: Perform system cleanup and maintenance tasks

## 🔐 Security Features

- **Password Hashing**: bcrypt for secure password storage
- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Protection**: Parameterized queries
- **CORS Configuration**: Secure cross-origin requests
- **File Upload Security**: Type and size validation

## 🚀 API Endpoints

### Authentication
- `POST /api/register` - User registration
- `POST /api/login` - User login
- `POST /api/logout` - User logout

### Agents
- `GET /api/agents` - List all agents
- `GET /api/agents/{agent_id}` - Get agent details

### Chat
- `GET /api/chat/history/{user_id}` - Get chat history
- `GET /api/conversation/{conversation_id}` - Get conversation messages
- `WebSocket /ws` - Real-time chat communication

### Admin (Protected)
- `GET /api/admin/stats` - System statistics
- `GET /api/admin/users` - User management
- `POST /api/admin/agents` - Create agent
- `PUT /api/admin/agents/{agent_id}` - Update agent
- `DELETE /api/admin/agents/{agent_id}` - Delete agent

### Payments
- `POST /api/create-payment-intent` - Create payment intent
- `POST /api/verify-payment` - Verify payment completion

## 🧪 Development

### Running in Development Mode
```bash
# Start with auto-reload
python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload

# Enable debug logging
export LOG_LEVEL=DEBUG
```

### Database Migrations
The application automatically creates required tables on startup. For manual database management:

```python
from database import Database
import asyncio

# Initialize database
asyncio.run(Database().init_database())
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Contact: support@agencore.com
- Documentation: See inline code comments and this README

## 🔄 Version History

- **v1.0.0** - Initial release with core functionality
- **v1.1.0** - Added admin panel and agent management
- **v1.2.0** - Enhanced UI/UX and mobile responsiveness
- **v1.3.0** - Added voice input and prompt enhancement
- **v1.4.0** - Complete English translation and improved admin features

---

**AgentCore** - Empowering users with specialized AI agents for every task.
