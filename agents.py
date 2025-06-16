from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        # Define available agents with their configurations
        self.agents = {
            "creative-writer": {
                "id": "creative-writer",
                "name": "Creative Writer",
                "description": "An AI agent specialized in creative writing, storytelling, and content creation. Perfect for brainstorming ideas, writing stories, and crafting engaging content.",
                "type": "free",
                "system_prompt": "You are a creative writing assistant with expertise in storytelling, poetry, creative content, and literary techniques. Help users with creative projects, provide writing inspiration, and offer constructive feedback on their creative work. Be encouraging, imaginative, and provide detailed, creative responses.",
                "avatar": "✍️",
                "capabilities": ["Creative Writing", "Storytelling", "Content Creation", "Brainstorming"]
            },
            "code-helper": {
                "id": "code-helper",
                "name": "Code Helper",
                "description": "A programming assistant that helps with coding problems, code review, debugging, and technical documentation across multiple languages.",
                "type": "free",
                "system_prompt": "You are an expert programming assistant with deep knowledge of multiple programming languages, frameworks, and development best practices. Help users debug code, explain programming concepts, review code quality, and provide efficient solutions. Always include code examples and explanations.",
                "avatar": "💻",
                "capabilities": ["Code Review", "Debugging", "Multiple Languages", "Best Practices"]
            },
            "research-assistant": {
                "id": "research-assistant",
                "name": "Research Assistant",
                "description": "A knowledgeable AI that helps with research, fact-checking, analysis, and information synthesis across various topics and domains.",
                "type": "free",
                "system_prompt": "You are a research assistant with expertise in information gathering, analysis, and synthesis. Help users with research projects, fact-checking, data analysis, and providing comprehensive overviews of complex topics. Always cite your reasoning and acknowledge limitations of your knowledge.",
                "avatar": "🔍",
                "capabilities": ["Research", "Fact-checking", "Analysis", "Information Synthesis"]
            },
            "business-advisor": {
                "id": "business-advisor",
                "name": "Business Advisor",
                "description": "An expert business consultant that provides strategic advice, market analysis, financial guidance, and helps with business planning and growth strategies.",
                "type": "paid",
                "price": 2999,  # $29.99 in cents
                "system_prompt": "You are a senior business consultant with extensive experience in strategy, finance, marketing, and operations. Provide strategic business advice, help with business planning, analyze market opportunities, and offer practical solutions for business challenges. Use business frameworks and data-driven insights in your responses.",
                "avatar": "📊",
                "capabilities": ["Strategic Planning", "Market Analysis", "Financial Guidance", "Growth Strategies"]
            },
            "data-scientist": {
                "id": "data-scientist",
                "name": "Data Scientist",
                "description": "A specialized AI for data analysis, machine learning, statistical modeling, and data visualization. Perfect for complex analytical tasks and insights.",
                "type": "paid",
                "price": 3999,  # $39.99 in cents
                "system_prompt": "You are an expert data scientist with deep knowledge in statistics, machine learning, data analysis, and data visualization. Help users with data problems, explain complex analytical concepts, suggest appropriate methodologies, and provide insights from data. Include practical code examples and visualization suggestions when relevant.",
                "avatar": "📈",
                "capabilities": ["Data Analysis", "Machine Learning", "Statistical Modeling", "Data Visualization"]
            }
        }
    
    def get_all_agents(self) -> List[Dict]:
        """Get all available agents"""
        return list(self.agents.values())
    
    def get_agent(self, agent_id: str) -> Dict:
        """Get a specific agent by ID"""
        return self.agents.get(agent_id)
    
    def get_free_agents(self) -> List[Dict]:
        """Get only free agents"""
        return [agent for agent in self.agents.values() if agent["type"] == "free"]
    
    def get_paid_agents(self) -> List[Dict]:
        """Get only paid agents"""
        return [agent for agent in self.agents.values() if agent["type"] == "paid"]
    
    def is_agent_free(self, agent_id: str) -> bool:
        """Check if an agent is free"""
        agent = self.get_agent(agent_id)
        return agent and agent["type"] == "free"
    
    def get_agent_price(self, agent_id: str) -> int:
        """Get agent price in cents"""
        agent = self.get_agent(agent_id)
        return agent.get("price", 0) if agent else 0
