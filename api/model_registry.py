# -*- coding: utf-8 -*-

TAG_UNIVERSAL = "万能"
TAG_ANIME = "アニメイラスト向け"
TAG_REALISTIC = "実写向け"
TAG_NSFW = "NSFW対応"

MODEL_REGISTRY = {
    # OpenAI Models
    "openai-gpt-image-2": {
        "id": "openai-gpt-image-2",
        "display_name": "OpenAI - GPT Image 2",
        "provider": "openai",
        "endpoint": "gpt-image-2",
        "category": "both",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "OpenAIの最高峰フラグシップモデル。指示追従性とディテール表現に優れ、プロンプトに忠実な万能描画が可能です。",
        "sizes": [
            {"label": "1024x1024 (1:1)", "value": "1024x1024"},
            {"label": "1280x720 (16:9)", "value": "1280x720"},
            {"label": "720x1280 (9:16)", "value": "720x1280"},
            {"label": "768x1024 (3:4)", "value": "768x1024"},
            {"label": "1024x768 (4:3)", "value": "1024x768"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": True,
        "estimated_cost": 0.04,
        # Quality is controlled by the dedicated Standard/High Quality radio
        # buttons in PromptPanel; duplicating it here caused the default to
        # overwrite the visible selection.
        "expert_params": []
    },
    
    # fal.ai FLUX Family (Verified Real Endpoints)
    "fal-flux-2-pro": {
        "id": "fal-flux-2-pro",
        "display_name": "fal.ai - FLUX.2 Pro",
        "provider": "fal",
        "endpoint": "fal-ai/flux-2-pro",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "Black Forest Labs最新FLUX.2 Proモデル。超高精細な質感・光彩・正確な文字描画に対応。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.03,
        "expert_params": [
            {
                "name": "seed",
                "label": "Seed",
                "type": "integer",
                "placeholder": "Random (Leave empty)"
            },
            {
                "name": "safety_tolerance",
                "label": "Safety Tolerance",
                "type": "select",
                "options": [
                    {"label": "1 (Strict)", "value": "1"},
                    {"label": "2", "value": "2"},
                    {"label": "3", "value": "3"},
                    {"label": "4", "value": "4"},
                    {"label": "5", "value": "5"}
                ],
                "default": "5"
            },
            {
                "name": "enable_safety_checker",
                "label": "Safety Checker",
                "type": "select",
                "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}],
                "default": "false"
            },
            {
                "name": "output_format",
                "label": "Output Format",
                "type": "select",
                "options": [{"label": "JPEG", "value": "jpeg"}, {"label": "PNG", "value": "png"}],
                "default": "png"
            }
        ]
    },
    "fal-flux-pro-v11": {
        "id": "fal-flux-pro-v11",
        "display_name": "fal.ai - FLUX 1.1 [pro]",
        "provider": "fal",
        "endpoint": "fal-ai/flux-pro/v1.1",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "Black Forest Labs最高峰FLUX 1.1 Proモデル。圧倒的な質感・解像感と高速生成を両立。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.04,
        "expert_params": [
            {
                "name": "seed",
                "label": "Seed",
                "type": "integer",
                "placeholder": "Random (Leave empty)"
            },
            {
                "name": "enable_safety_checker",
                "label": "Safety Checker",
                "type": "select",
                "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}],
                "default": "false"
            },
            {
                "name": "output_format",
                "label": "Output Format",
                "type": "select",
                "options": [{"label": "JPEG", "value": "jpeg"}, {"label": "PNG", "value": "png"}],
                "default": "png"
            }
        ]
    },
    "fal-flux-1-dev": {
        "id": "fal-flux-1-dev",
        "display_name": "fal.ai - FLUX.1 [dev]",
        "provider": "fal",
        "endpoint": "fal-ai/flux/dev",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "FLUX.1の高解像度Devモデル。きめ細やかなディテールとフォトリアルな写真・風景描写に優れています。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.025,
        "expert_params": [
            {
                "name": "num_inference_steps",
                "label": "Inference Steps",
                "type": "integer",
                "placeholder": "28",
                "default": 28,
                "min": 1,
                "max": 50
            },
            {
                "name": "guidance_scale",
                "label": "Guidance Scale",
                "type": "float",
                "placeholder": "3.5",
                "default": 3.5,
                "min": 0.0,
                "max": 20.0
            },
            {
                "name": "seed",
                "label": "Seed",
                "type": "integer",
                "placeholder": "Random (Leave empty)"
            },
            {
                "name": "enable_safety_checker",
                "label": "Safety Checker",
                "type": "select",
                "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}],
                "default": "false"
            }
        ]
    },
    "fal-flux-schnell": {
        "id": "fal-flux-schnell",
        "display_name": "fal.ai - FLUX.1 [schnell]",
        "provider": "fal",
        "endpoint": "fal-ai/flux/schnell",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "わずか4ステップで生成する超高速FLUXモデル。アイデアやプロンプト案の高速検証に最適。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.003,
        "expert_params": [
            {"name": "num_inference_steps", "label": "Inference Steps", "type": "integer", "placeholder": "4", "default": 4, "min": 1, "max": 12},
            {"name": "seed", "label": "Seed", "type": "integer", "placeholder": "Random (Leave empty)"},
            {"name": "enable_safety_checker", "label": "Safety Checker", "type": "select", "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}], "default": "false"},
            {"name": "output_format", "label": "Output Format", "type": "select", "options": [{"label": "PNG", "value": "png"}, {"label": "JPEG", "value": "jpeg"}, {"label": "WEBP", "value": "webp"}], "default": "png"}
        ]
    },
    "fal-flux-lora": {
        "id": "fal-flux-lora",
        "display_name": "fal.ai - FLUX-LoRA",
        "provider": "fal",
        "endpoint": "fal-ai/flux-lora",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_ANIME, TAG_REALISTIC],
        "description": "任意のCivitai/HF等のLoRA URL（アニメ・実写キャラ等）や重みスケールを指定してカスタム生成可能なFLUXモデル。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.03,
        "expert_params": [
            {"name": "num_inference_steps", "label": "Inference Steps", "type": "integer", "placeholder": "28", "default": 28, "min": 1, "max": 50},
            {"name": "guidance_scale", "label": "Guidance Scale", "type": "float", "placeholder": "3.5", "default": 3.5, "min": 0.0, "max": 20.0},
            {"name": "lora_path", "label": "LoRA URL / Path", "type": "string", "placeholder": "https://civitai.com/... or HF model path"},
            {"name": "lora_scale", "label": "LoRA Weight Scale", "type": "float", "placeholder": "1.0", "default": 1.0, "min": 0.0, "max": 3.0},
            {"name": "seed", "label": "Seed", "type": "integer", "placeholder": "Random (Leave empty)"},
            {"name": "enable_safety_checker", "label": "Safety Checker", "type": "select", "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}], "default": "false"}
        ]
    },

    # SDXL & Base Models on fal.ai
    "fal-fast-sdxl": {
        "id": "fal-fast-sdxl",
        "display_name": "fal.ai - Fast SDXL (Turbo / Lightning)",
        "provider": "fal",
        "endpoint": "fal-ai/fast-sdxl",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "SDXL Turbo/Lightning技術により高速で綺麗な画像を生成する実用モデル。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": True,
        "estimated_cost": 0.003,
        "expert_params": [
            {"name": "num_inference_steps", "label": "Inference Steps", "type": "integer", "placeholder": "8", "default": 8, "min": 1, "max": 20},
            {"name": "guidance_scale", "label": "Guidance Scale", "type": "float", "placeholder": "2.0", "default": 2.0, "min": 0.0, "max": 10.0},
            {"name": "seed", "label": "Seed", "type": "integer", "placeholder": "Random (Leave empty)"},
            {"name": "enable_safety_checker", "label": "Safety Checker", "type": "select", "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}], "default": "false"}
        ]
    },
    "fal-stable-diffusion-v15": {
        "id": "fal-stable-diffusion-v15",
        "display_name": "fal.ai - Stable Diffusion v1.5",
        "provider": "fal",
        "endpoint": "fal-ai/stable-diffusion-v15",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_NSFW],
        "description": "最も豊富な学習モデル・拡張機能エコシステムを持つ基盤モデル。自由度が高いのが特徴。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": True,
        "estimated_cost": 0.002,
        "expert_params": [
            {"name": "num_inference_steps", "label": "Inference Steps", "type": "integer", "placeholder": "20", "default": 20, "min": 1, "max": 50},
            {"name": "guidance_scale", "label": "Guidance Scale", "type": "float", "placeholder": "7.5", "default": 7.5, "min": 1.0, "max": 20.0},
            {"name": "seed", "label": "Seed", "type": "integer", "placeholder": "Random (Leave empty)"},
            {"name": "enable_safety_checker", "label": "Safety Checker", "type": "select", "options": [{"label": "Off", "value": "false"}, {"label": "On", "value": "true"}], "default": "false"}
        ]
    },
    "fal-fooocus": {
        "id": "fal-fooocus",
        "display_name": "fal.ai - Fooocus (SDXL Engine)",
        "provider": "fal",
        "endpoint": "fal-ai/fooocus",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_ANIME, TAG_REALISTIC],
        "description": "Fooocusオートチューニング版SDXL。専門知識なしでプロレベルのアニメ・実写画像を自動生成。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": True,
        "estimated_cost": 0.005,
        "expert_params": [
            {"name": "performance", "label": "Performance Mode", "type": "select", "options": [{"label": "Speed", "value": "Speed"}, {"label": "Quality", "value": "Quality"}], "default": "Speed"}
        ]
    },

    # Specialized Design Models on fal.ai
    "fal-recraft-v3": {
        "id": "fal-recraft-v3",
        "display_name": "fal.ai - Recraft V3",
        "provider": "fal",
        "endpoint": "fal-ai/recraft-v3",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_ANIME, TAG_REALISTIC],
        "description": "グラフィックデザイン・ベクターアート・ブランドデザインに圧倒的に強いハイエンドモデル。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.04,
        "expert_params": []
    },
    "fal-ideogram-v3": {
        "id": "fal-ideogram-v3",
        "display_name": "fal.ai - Ideogram V3",
        "provider": "fal",
        "endpoint": "fal-ai/ideogram-v3",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "画像内の英字・文字タイポグラフィ描画において業界トップレベルのデザイン重視モデル。",
        "sizes": [
            {"label": "Square HD (1:1)", "value": "square_hd"},
            {"label": "Landscape 16:9", "value": "landscape_16_9"},
            {"label": "Portrait 16:9", "value": "portrait_16_9"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.08,
        "expert_params": []
    },

    # Grok Imagine (on fal.ai)
    "fal-grok-imagine-standard": {
        "id": "fal-grok-imagine-standard",
        "display_name": "fal.ai - Grok Imagine Standard",
        "provider": "fal",
        "endpoint": "xai/grok-imagine-image",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "xAIのAuroraエンジン。力強い光表現とシネマティックなアート・写真描写が得意。",
        "sizes": [
            {"label": "1:1 Square", "value": "square"},
            {"label": "16:9 Landscape", "value": "landscape_16_9"},
            {"label": "9:16 Portrait", "value": "portrait_16_9"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.02,
        "expert_params": [
            {
                "name": "upsample_prompt",
                "label": "Upsample Prompt",
                "type": "select",
                "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}],
                "default": "true"
            }
        ]
    },
    "fal-grok-imagine-quality": {
        "id": "fal-grok-imagine-quality",
        "display_name": "fal.ai - Grok Imagine Quality",
        "provider": "fal",
        "endpoint": "xai/grok-imagine-image/quality/text-to-image",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "Grok Imagineの最高品質モード。よりきめ細やかでドラマチックな出力が可能です。",
        "sizes": [
            {"label": "1:1 Square", "value": "square"},
            {"label": "16:9 Landscape", "value": "landscape_16_9"},
            {"label": "9:16 Portrait", "value": "portrait_16_9"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.05,
        "expert_params": [
            {
                "name": "upsample_prompt",
                "label": "Upsample Prompt",
                "type": "select",
                "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}],
                "default": "true"
            }
        ]
    },
    "fal-grok-imagine-edit": {
        "id": "fal-grok-imagine-edit",
        "display_name": "fal.ai - Grok Imagine Edit",
        "provider": "fal",
        "endpoint": "xai/grok-imagine-image/quality/edit",
        "category": "img_edit",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "Grok Imagineによる高品質画像編集・指示変換エンジン。",
        "sizes": [
            {"label": "Auto", "value": "auto"}
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.05,
        "expert_params": [
            {
                "name": "upsample_prompt",
                "label": "Upsample Prompt",
                "type": "select",
                "options": [{"label": "True", "value": "true"}, {"label": "False", "value": "false"}],
                "default": "true"
            }
        ]
    },

    # GPT Image 2 (on fal.ai)
    "fal-gpt-image-2": {
        "id": "fal-gpt-image-2",
        "display_name": "fal.ai - GPT Image 2",
        "provider": "fal",
        "endpoint": "fal-ai/gpt-image-2",
        "category": "both",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "fal.aiインフラ経由で動作するGPT Image 2モデル。",
        "sizes": [
            {"label": "1:1 Square", "value": "square"},
            {"label": "16:9 Landscape", "value": "landscape_16_9"},
            {"label": "9:16 Portrait", "value": "portrait_16_9"},
        ],
        "default_enabled": False,
        "supports_negative_prompt": True,
        "estimated_cost": 0.04,
        "expert_params": [
            {
                "name": "quality",
                "label": "Quality",
                "type": "select",
                "options": [{"label": "Standard", "value": "standard"}, {"label": "HD", "value": "hd"}],
                "default": "standard"
            }
        ]
    },

    # Qwen Image 2.0 (on fal.ai)
    "fal-qwen-image-2": {
        "id": "fal-qwen-image-2",
        "display_name": "fal.ai - Qwen Image 2.0",
        "provider": "fal",
        "endpoint": "fal-ai/qwen-image-2",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_ANIME],
        "description": "Alibaba開発。東洋美術・アニメイラスト・ファンタジー描写に長けたアジアンデザインモデル。",
        "sizes": [
            {"label": "1:1 Square", "value": "square"},
            {"label": "16:9 Landscape", "value": "landscape_16_9"},
            {"label": "9:16 Portrait", "value": "portrait_16_9"},
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.035,
        "expert_params": [
            {
                "name": "seed",
                "label": "Seed",
                "type": "integer",
                "placeholder": "Random (Leave empty)"
            },
            {
                "name": "output_format",
                "label": "Output Format",
                "type": "select",
                "options": [{"label": "PNG", "value": "png"}, {"label": "JPEG", "value": "jpeg"}, {"label": "WEBP", "value": "webp"}],
                "default": "png"
            }
        ]
    },
    "fal-qwen-image-2-edit": {
        "id": "fal-qwen-image-2-edit",
        "display_name": "fal.ai - Qwen Image 2.0 Edit",
        "provider": "fal",
        "endpoint": "fal-ai/qwen-image-2/edit",
        "category": "img_edit",
        "tags": [TAG_UNIVERSAL, TAG_ANIME],
        "description": "Qwen Image 2.0による画像編集・イラストアレンジ機能。",
        "sizes": [
            {"label": "Auto", "value": "auto"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.035,
        "expert_params": [
            {
                "name": "seed",
                "label": "Seed",
                "type": "integer",
                "placeholder": "Random (Leave empty)"
            }
        ]
    },

    # Seedream 5.0 (on fal.ai)
    "fal-seedream-5-pro": {
        "id": "fal-seedream-5-pro",
        "display_name": "fal.ai - Seedream 5.0 Pro",
        "provider": "fal",
        "endpoint": "bytedance/seedream/v5/pro/text-to-image",
        "category": "text2img",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "ByteDanceが誇るプロダクション品質エンジン。商用レベルの美しさと一貫性を誇ります。",
        "sizes": [
            {"label": "1:1 Square", "value": "square"},
            {"label": "16:9 Landscape", "value": "landscape_16_9"},
            {"label": "9:16 Portrait", "value": "portrait_16_9"},
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.0675,
        "expert_params": []
    },
    "fal-seedream-5-pro-edit": {
        "id": "fal-seedream-5-pro-edit",
        "display_name": "fal.ai - Seedream 5.0 Pro Edit",
        "provider": "fal",
        "endpoint": "bytedance/seedream/v5/pro/edit",
        "category": "img_edit",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "Seedream 5.0による高精度画像編集エンジン。",
        "sizes": [
            {"label": "Auto", "value": "auto"}
        ],
        "default_enabled": False,
        "supports_negative_prompt": False,
        "estimated_cost": 0.0675,
        "expert_params": []
    },

    # Grok Models (xAI Direct)
    "xai-grok-imagine-quality": {
        "id": "xai-grok-imagine-quality",
        "display_name": "Grok - Imagine Quality (Direct)",
        "provider": "xai",
        "endpoint": "grok-imagine-image-quality",
        "category": "both",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "xAI API直接通信の高品質Grok Imagine。写真・リアル・アート表現を高精細に生成。",
        "sizes": [
            {"label": "1:1 Square", "value": "1:1"},
            {"label": "16:9 Landscape", "value": "16:9"},
            {"label": "9:16 Portrait", "value": "9:16"},
            {"label": "4:3 Standard", "value": "4:3"},
            {"label": "3:4 Tall", "value": "3:4"},
            {"label": "3:2 Photo", "value": "3:2"},
            {"label": "2:3 Portrait Photo", "value": "2:3"},
            {"label": "21:9 Wide", "value": "21:9"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.05,
        "expert_params": []
    },
    "xai-grok-imagine-standard": {
        "id": "xai-grok-imagine-standard",
        "display_name": "Grok - Imagine Standard (Direct)",
        "provider": "xai",
        "endpoint": "grok-imagine-image",
        "category": "both",
        "tags": [TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "xAI API直接通信の標準Grok Imagine。スピーディで高品質な画像生成。",
        "sizes": [
            {"label": "1:1 Square", "value": "1:1"},
            {"label": "16:9 Landscape", "value": "16:9"},
            {"label": "9:16 Portrait", "value": "9:16"},
            {"label": "4:3 Standard", "value": "4:3"},
            {"label": "3:4 Tall", "value": "3:4"},
            {"label": "3:2 Photo", "value": "3:2"},
            {"label": "2:3 Portrait Photo", "value": "2:3"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.02,
        "expert_params": []
    },

    # HotAPI Models (Uncensored Multi-modal Gateway)
    "hotapi-z-image-spicy": {
        "id": "hotapi-z-image-spicy",
        "display_name": "HotAPI - Z-Image Spicy (Uncensored)",
        "provider": "hotapi",
        "endpoint": "z-image-spicy",
        "category": "text2img",
        "tags": [TAG_NSFW, TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "HotAPIが無検閲で提供する高速・高精細画像生成モデル。プロンプト制限・フィルターなし。",
        "sizes": [
            {"label": "1024x1024 (1:1)", "value": "1024x1024"},
            {"label": "1024x576 (16:9)", "value": "1024x576"},
            {"label": "576x1024 (9:16)", "value": "576x1024"},
            {"label": "1024x768 (4:3)", "value": "1024x768"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.024,
        "expert_params": []
    },
    "hotapi-seedream-50-lite-spicy": {
        "id": "hotapi-seedream-50-lite-spicy",
        "display_name": "HotAPI - SeeDream 5.0 Lite Spicy (Uncensored)",
        "provider": "hotapi",
        "endpoint": "seedream-5.0-lite-spicy",
        "category": "both",
        "tags": [TAG_NSFW, TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "SeeDream 5.0 Lite無検閲版。テキスト生成および画像編集・マルチ画像合成に対応。",
        "sizes": [
            {"label": "1024x1024 (1:1)", "value": "1024x1024"},
            {"label": "1280x720 (16:9)", "value": "1280x720"},
            {"label": "720x1280 (9:16)", "value": "720x1280"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.03,
        "expert_params": []
    },
    "hotapi-seedream-50-pro-spicy": {
        "id": "hotapi-seedream-50-pro-spicy",
        "display_name": "HotAPI - SeeDream 5.0 Pro Spicy (Uncensored)",
        "provider": "hotapi",
        "endpoint": "seedream-5.0-pro-spicy",
        "category": "both",
        "tags": [TAG_NSFW, TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "SeeDream 5.0 Pro最高峰無検閲モデル。卓越した美しさとプロレベルの表現力。",
        "sizes": [
            {"label": "1024x1024 (1:1)", "value": "1024x1024"},
            {"label": "1280x720 (16:9)", "value": "1280x720"},
            {"label": "720x1280 (9:16)", "value": "720x1280"},
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.06,
        "expert_params": []
    },
    "hotapi-qwen-image-edit-spicy": {
        "id": "hotapi-qwen-image-edit-spicy",
        "display_name": "HotAPI - Qwen Image Edit Spicy (Uncensored)",
        "provider": "hotapi",
        "endpoint": "qwen-image-edit-spicy",
        "category": "img_edit",
        "tags": [TAG_NSFW, TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "Qwen Image Edit無検閲版。参照画像に対する高度な命令編集・改変に対応。",
        "sizes": [
            {"label": "Auto (auto)", "value": "auto"}
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.035,
        "expert_params": []
    },
    "hotapi-face-swap-spicy": {
        "id": "hotapi-face-swap-spicy",
        "display_name": "HotAPI - Face Swap Spicy (Uncensored)",
        "provider": "hotapi",
        "endpoint": "face-swap-spicy",
        "category": "img_edit",
        "tags": [TAG_NSFW, TAG_UNIVERSAL, TAG_REALISTIC],
        "description": "無検閲Face Swapモデル。ターゲット画像と元顔画像（face_image）による顔置換。",
        "sizes": [
            {"label": "Auto (auto)", "value": "auto"}
        ],
        "default_enabled": True,
        "supports_negative_prompt": False,
        "estimated_cost": 0.04,
        "expert_params": [
            {
                "name": "face_image",
                "label": "Source Face Image Path (置換元の顔画像パス)",
                "type": "filepath",
                "placeholder": "Select or enter source face image path..."
            }
        ]
    }
}
