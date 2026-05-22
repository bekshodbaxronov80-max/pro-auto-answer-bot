"""
20 ta AI Chat API provayderlari uchun universal ulanish moduli.
Barcha API lar uchun yagona interfeys.
"""
import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any


class AIProvider:
    """AI API provayderlarini boshqarish klassi."""
    
    PROVIDERS = {
        # ========== OPENAI EKOTIZIMI ==========
        "openai": {
            "name": "OpenAI (GPT-4/GPT-3.5)",
            "url": "https://api.openai.com/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "gpt-4o-mini",
            "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "format": "openai",
            "description": "Eng mashhur AI, 100+ til"
        },
        
        # ========== ANTHROPIC ==========
        "claude": {
            "name": "Claude (Anthropic)",
            "url": "https://api.anthropic.com/v1/messages",
            "headers": lambda key: {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            "default_model": "claude-3-haiku-20240307",
            "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "format": "claude",
            "description": "Eng xavfsiz AI, uzoq kontekst"
        },
        
        # ========== GOOGLE ==========
        "gemini": {
            "name": "Google Gemini",
            "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            "headers": lambda key: {"Content-Type": "application/json"},
            "default_model": "gemini-pro",
            "models": ["gemini-pro", "gemini-1.5-pro", "gemini-1.5-flash"],
            "format": "gemini",
            "url_suffix": lambda key: f"?key={key}",
            "description": "Google AI, bepul daraja bor"
        },
        
        # ========== DEEPSEEK ==========
        "deepseek": {
            "name": "DeepSeek",
            "url": "https://api.deepseek.com/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "deepseek-chat",
            "models": ["deepseek-chat", "deepseek-coder"],
            "format": "openai",
            "description": "Arzon va kuchli Xitoy AI"
        },
        
        # ========== MISTRAL ==========
        "mistral": {
            "name": "Mistral AI",
            "url": "https://api.mistral.ai/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "mistral-small",
            "models": ["mistral-large", "mistral-medium", "mistral-small"],
            "format": "openai",
            "description": "Yevropa AI, ochiq kodli"
        },
        
        # ========== META ==========
        "llama": {
            "name": "Meta Llama (Groq)",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "llama-3.1-8b-instant",
            "models": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "llama-3.2-3b-preview"],
            "format": "openai",
            "description": "Meta AI, Groq orqali tekin"
        },
        
        # ========== COHERE ==========
        "cohere": {
            "name": "Cohere",
            "url": "https://api.cohere.ai/v1/chat",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "Accept": "application/json"},
            "default_model": "command-r-plus",
            "models": ["command-r-plus", "command-r", "command"],
            "format": "cohere",
            "description": "Enterprise AI, yaxshi RAG"
        },
        
        # ========== XAI (GROK) ==========
        "grok": {
            "name": "Grok (xAI)",
            "url": "https://api.x.ai/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "grok-beta",
            "models": ["grok-beta", "grok-1"],
            "format": "openai",
            "description": "Elon Musk AI"
        },
        
        # ========== PERPLEXITY ==========
        "perplexity": {
            "name": "Perplexity AI",
            "url": "https://api.perplexity.ai/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "llama-3.1-sonar-small-128k-online",
            "models": ["llama-3.1-sonar-large-128k-online", "llama-3.1-sonar-small-128k-online"],
            "format": "openai",
            "description": "Internet bilan ishlaydigan AI"
        },
        
        # ========== TOGETHER AI ==========
        "together": {
            "name": "Together AI",
            "url": "https://api.together.xyz/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "models": ["mistralai/Mixtral-8x7B-Instruct-v0.1", "meta-llama/Llama-3-70b-chat-hf"],
            "format": "openai",
            "description": "Ko'p ochiq model hosting"
        },
        
        # ========== REPLICATE ==========
        "replicate": {
            "name": "Replicate",
            "url": "https://api.replicate.com/v1/predictions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "meta/llama-2-70b-chat",
            "models": ["meta/llama-2-70b-chat", "mistralai/mistral-7b-instruct-v0.2"],
            "format": "replicate",
            "description": "Ochiq modellarni ishga tushirish"
        },
        
        # ========== HUGGING FACE ==========
        "huggingface": {
            "name": "Hugging Face",
            "url": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "mistralai/Mistral-7B-Instruct-v0.3",
            "models": ["mistralai/Mistral-7B-Instruct-v0.3", "meta-llama/Llama-2-7b-chat-hf"],
            "format": "huggingface",
            "description": "Eng katta ochiq model kutubxonasi"
        },
        
        # ========== AI21 LABS ==========
        "ai21": {
            "name": "AI21 Labs (Jurassic)",
            "url": "https://api.ai21.com/studio/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "jamba-1.5-mini",
            "models": ["jamba-1.5-large", "jamba-1.5-mini"],
            "format": "openai",
            "description": "Isroil AI, 256K kontekst"
        },
        
        # ========== ZHIPU AI (GLM) ==========
        "zhipu": {
            "name": "Zhipu AI (GLM)",
            "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "glm-4",
            "models": ["glm-4", "glm-4v", "glm-3-turbo"],
            "format": "openai",
            "description": "Xitoy AI, GLM modeli"
        },
        
        # ========== BAICHUAN ==========
        "baichuan": {
            "name": "Baichuan AI",
            "url": "https://api.baichuan-ai.com/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "Baichuan4",
            "models": ["Baichuan4", "Baichuan3-Turbo"],
            "format": "openai",
            "description": "Xitoy AI, yaxshi xitoy tili"
        },
        
        # ========== QWEN (ALIBABA) ==========
        "qwen": {
            "name": "Qwen (Alibaba)",
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "qwen-turbo",
            "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
            "format": "openai",
            "description": "Alibaba AI, Xitoy bozori"
        },
        
        # ========== YANDEX GPT ==========
        "yandex": {
            "name": "Yandex GPT",
            "url": "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            "headers": lambda key: {"Authorization": f"Api-Key {key}", "Content-Type": "application/json"},
            "default_model": "yandexgpt-lite",
            "models": ["yandexgpt", "yandexgpt-lite"],
            "format": "yandex",
            "description": "Rossiya AI, yaxshi rus tili"
        },
        
        # ========== AMAZON BEDROCK ==========
        "bedrock": {
            "name": "Amazon Bedrock",
            "url": "https://bedrock-runtime.{region}.amazonaws.com",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            "default_model": "anthropic.claude-3-haiku-20240307-v1:0",
            "models": ["anthropic.claude-3-sonnet-20240229-v1:0", "anthropic.claude-3-haiku-20240307-v1:0"],
            "format": "bedrock",
            "description": "AWS AI, korporativ yechim"
        },
        
        # ========== OPENROUTER ==========
        "openrouter": {
            "name": "OpenRouter",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://t.me", "X-Title": "Telegram Bot"},
            "default_model": "openai/gpt-4o-mini",
            "models": ["openai/gpt-4o", "anthropic/claude-3-opus", "google/gemini-pro", "meta-llama/llama-3.1-70b"],
            "format": "openai",
            "description": "200+ modelga yagona API"
        }
    }
    
    @staticmethod
    def get_providers_list() -> Dict[str, str]:
        """Barcha provayderlar ro'yxatini qaytaradi."""
        return {key: info["name"] for key, info in AIProvider.PROVIDERS.items()}
    
    @staticmethod
    def get_models(provider: str) -> list:
        """Provayder modellarini qaytaradi."""
        info = AIProvider.PROVIDERS.get(provider)
        return info["models"] if info else []
    
    @staticmethod
    async def send_request(provider: str, api_key: str, message: str, 
                          system_prompt: str = None, model: str = None) -> Dict[str, Any]:
        """
        AI API ga so'rov yuborish.
        
        Args:
            provider: Provayder kodi (openai, claude, gemini...)
            api_key: API kaliti
            message: Foydalanuvchi xabari
            system_prompt: Tizim promti
            model: Model nomi (agar ko'rsatilmagan bo'lsa, default)
            
        Returns:
            {"success": True/False, "reply": "...", "error": "...", "model": "..."}
        """
        
        provider_info = AIProvider.PROVIDERS.get(provider)
        if not provider_info:
            return {"success": False, "error": f"Noma'lum provayder: {provider}"}
        
        if not model:
            model = provider_info["default_model"]
        
        url = provider_info["url"]
        headers = provider_info["headers"](api_key)
        
        # URL ga key qo'shish (Gemini uchun)
        if "url_suffix" in provider_info:
            url = url + provider_info["url_suffix"](api_key)
        
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                
                # ========== OPENAI FORMATI ==========
                if provider_info["format"] == "openai":
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": message})
                    
                    data = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if "choices" in result:
                            return {
                                "success": True,
                                "reply": result["choices"][0]["message"]["content"],
                                "model": result.get("model", model)
                            }
                        else:
                            error_msg = result.get("error", {}).get("message", str(result))
                            return {"success": False, "error": error_msg}
                
                # ========== CLAUDE FORMATI ==========
                elif provider_info["format"] == "claude":
                    messages = [{"role": "user", "content": message}]
                    data = {
                        "model": model,
                        "max_tokens": 2000,
                        "messages": messages
                    }
                    if system_prompt:
                        data["system"] = system_prompt
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if "content" in result:
                            return {
                                "success": True,
                                "reply": result["content"][0]["text"],
                                "model": result.get("model", model)
                            }
                        else:
                            error_msg = result.get("error", {}).get("message", str(result))
                            return {"success": False, "error": error_msg}
                
                # ========== GEMINI FORMATI ==========
                elif provider_info["format"] == "gemini":
                    parts = [{"text": message}]
                    data = {"contents": [{"parts": parts}]}
                    
                    if system_prompt:
                        data["systemInstruction"] = {"parts": [{"text": system_prompt}]}
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if "candidates" in result:
                            text = result["candidates"][0]["content"]["parts"][0]["text"]
                            return {
                                "success": True,
                                "reply": text,
                                "model": model
                            }
                        else:
                            error_msg = result.get("error", {}).get("message", str(result))
                            return {"success": False, "error": error_msg}
                
                # ========== COHERE FORMATI ==========
                elif provider_info["format"] == "cohere":
                    data = {
                        "model": model,
                        "message": message,
                        "max_tokens": 2000,
                        "temperature": 0.7
                    }
                    if system_prompt:
                        data["preamble"] = system_prompt
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if "text" in result:
                            return {
                                "success": True,
                                "reply": result["text"],
                                "model": model
                            }
                        else:
                            return {"success": False, "error": str(result)}
                
                # ========== YANDEX FORMATI ==========
                elif provider_info["format"] == "yandex":
                    messages = [{"role": "user", "text": message}]
                    if system_prompt:
                        messages.insert(0, {"role": "system", "text": system_prompt})
                    
                    data = {
                        "modelUri": f"gpt://{model}",
                        "completionOptions": {"maxTokens": 2000, "temperature": 0.7},
                        "messages": messages
                    }
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if "result" in result:
                            return {
                                "success": True,
                                "reply": result["result"]["alternatives"][0]["message"]["text"],
                                "model": model
                            }
                        else:
                            return {"success": False, "error": str(result)}
                
                # ========== HUGGINGFACE FORMATI ==========
                elif provider_info["format"] == "huggingface":
                    prompt = message
                    if system_prompt:
                        prompt = f"{system_prompt}\n\nUser: {message}"
                    
                    data = {"inputs": prompt, "parameters": {"max_new_tokens": 2000}}
                    
                    # URL ga model qo'shish
                    if model:
                        url = f"https://api-inference.huggingface.co/models/{model}"
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if isinstance(result, list) and len(result) > 0:
                            text = result[0].get("generated_text", "")
                            if prompt in text:
                                text = text.replace(prompt, "").strip()
                            return {
                                "success": True,
                                "reply": text or result[0].get("summary_text", str(result)),
                                "model": model
                            }
                        else:
                            return {"success": False, "error": str(result)}
                
                # ========== REPLICATE FORMATI ==========
                elif provider_info["format"] == "replicate":
                    prompt = message
                    if system_prompt:
                        prompt = f"System: {system_prompt}\n\nUser: {message}"
                    
                    data = {
                        "version": model,
                        "input": {"prompt": prompt, "max_tokens": 2000}
                    }
                    
                    async with session.post(url, json=data, headers=headers) as response:
                        result = await response.json()
                        
                        if "output" in result:
                            reply = result["output"]
                            if isinstance(reply, list):
                                reply = "".join(reply)
                            return {
                                "success": True,
                                "reply": reply,
                                "model": model
                            }
                        elif "status" in result and result["status"] == "processing":
                            return {
                                "success": False, 
                                "error": "Javob tayyorlanmoqda, qayta urinib ko'ring"
                            }
                        else:
                            return {"success": False, "error": str(result)}
                
                else:
                    return {"success": False, "error": f"Noma'lum format: {provider_info['format']}"}
                    
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Tarmoq xatoligi: {str(e)}"}
        except asyncio.TimeoutError:
            return {"success": False, "error": "So'rov vaqti tugadi (60s)"}
        except Exception as e:
            return {"success": False, "error": f"Xatolik: {str(e)}"}


# Tezkor sinov uchun
async def test_provider(provider: str, api_key: str):
    """Provayder ishlashini tekshirish."""
    result = await AIProvider.send_request(
        provider=provider,
        api_key=api_key,
        message="Salom! O'zingizni tanishtiring.",
        system_prompt="Sen foydali yordamchisan."
    )
    return result