# agentic-ai-cyberres
An AI agent that improves cyber resiliency by autonomously identifying enterprise applications and validating that the application's data is not corrupted.


# Pre-requisites
- Node.js (>= 18.0.0) runtime is needed to work with Bee Agent Framework.
- LLM Inference provider: e.g. watsonx, Ollama, Groq, OpenAI, GCP, AWS Bedrock 

# Installation
1. Clone the repository

<pre><code>git clone https://github.com/IBM/agentic-ai-cyberres.git
# or if repo requires a ssh key instead of password
git clone git@github.com:IBM/agentic-ai-cyberres.git
</code></pre> 

2. Change into working directory
<pre><code>cd agentic-ai-cyberres
</code></pre> 

3. Setup node.js

<pre><code>nvm install
</code></pre>

4. Install dependencies
<pre><code>npm ci
</code></pre>


5. Copy .env.template to .env
   
<pre><code>cp .env.template .env</code></pre>

6. Update .env to set your LLM provider and related settings.  

See [ibm.com/watsonx](ibm.com/watsonx) to try watsonx for free, which will also provide a project ID and API key.  You choose which region to use.
If using watsonx, set the API key, watsonx project ID and region as specified in your cloud account. Choose your watsonx model.
If using another model, set the LLM_BACKEND accordingly.
<pre><code>  
LLM_BACKEND="watsonx"
WATSONX_API_KEY=""
WATSONX_PROJECT_ID=""
WATSONX_MODEL="ibm/granite-3-8b-instruct"
WATSONX_REGION="us-south"
</code></pre>


7. Update .env to set the environment variables used by the agent's tools, to set email address and mongoDB name and collection
<pre><code># Variables for agentic-ai-cyberres data validation agent and tools
USER_EMAIL=""
MONGO_DB_CONN_STRING="mongodb://localhost"
MONGODB_NAME=""
MONGODB_COLLECTION_NAME=""</code></pre>
   
# Using agentic-ai-cyberres agent
<pre><code># to run interactively
npm run start src/agent.ts
</code></pre>
<pre><code># to run autonomously (e.g. through cron, ansible)
npm run start src/agent.ts <<< "Check if mongoDB is running and if so, validate the mongoDB database by passing in mongondb as a parameter"</code></pre>

