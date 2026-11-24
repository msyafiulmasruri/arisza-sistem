"""Llama 3.2 3B Instruct resmi dari Meta (Hugging Face).

Model dimuat saat pertama kali dibutuhkan, bukan saat Space menyala,
agar jalur prediksi model utama tetap cepat.
"""
import copy
import logging
import os
import threading
import time

log = logging.getLogger("arisza.llama")


class LlamaService:
    def __init__(self, model_id, hf_token="", dtype_name="bfloat16"):
        self.model_id = model_id
        self.hf_token = hf_token or None
        self.dtype_name = dtype_name
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None
        self.load_seconds = None

    @property
    def loaded(self):
        return self._model is not None

    def ensure_loaded(self):
        with self._lock:
            if self._model is not None:
                return
            os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from transformers.utils import logging as hf_logging

            hf_logging.set_verbosity_error()
            dtype = {
                "bfloat16": torch.bfloat16,
                "float16": torch.float16,
                "float32": torch.float32,
            }[self.dtype_name]

            log.info("Memuat model Llama %s (%s)...", self.model_id, self.dtype_name)
            mulai = time.perf_counter()
            tokenizer = AutoTokenizer.from_pretrained(self.model_id, token=self.hf_token)
            try:
                model = AutoModelForCausalLM.from_pretrained(self.model_id, token=self.hf_token, dtype=dtype)
            except TypeError:  # versi transformers lama memakai nama torch_dtype
                model = AutoModelForCausalLM.from_pretrained(self.model_id, token=self.hf_token, torch_dtype=dtype)
            model.eval()
            if getattr(model, "generation_config", None) is not None:
                model.generation_config.do_sample = False
                model.generation_config.temperature = 1.0
                model.generation_config.top_p = 1.0
                model.generation_config.top_k = 50
                if model.generation_config.pad_token_id is None:
                    eos = model.generation_config.eos_token_id
                    model.generation_config.pad_token_id = eos[0] if isinstance(eos, (list, tuple)) else eos
            self._tokenizer = tokenizer
            self._model = model
            self.load_seconds = round(time.perf_counter() - mulai, 2)
            log.info("Model Llama siap dalam %.2f detik", self.load_seconds)

    def count_input_tokens(self, messages):
        """Hitung token prompt sesuai chat template tokenizer Llama yang dimuat."""
        self.ensure_loaded()
        token_ids = self._tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True
        )
        if isinstance(token_ids, dict):
            token_ids = token_ids["input_ids"]
        if hasattr(token_ids, "shape"):
            return int(token_ids.shape[-1])
        if token_ids and isinstance(token_ids[0], (list, tuple)):
            return len(token_ids[0])
        return len(token_ids)

    def generate(self, messages, max_new_tokens):
        """Hasilkan teks secara deterministik (tanpa pengacakan)."""
        self.ensure_loaded()
        import torch

        inputs = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_dict=True, return_tensors="pt"
        )
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        panjang_masukan = inputs["input_ids"].shape[1]

        config = copy.deepcopy(self._model.generation_config)
        config.do_sample = False
        config.temperature = 1.0
        config.top_p = 1.0
        config.top_k = 50
        config.max_new_tokens = max_new_tokens
        if config.pad_token_id is None:
            eos = config.eos_token_id
            config.pad_token_id = eos[0] if isinstance(eos, (list, tuple)) else eos

        with torch.inference_mode():
            keluaran = self._model.generate(**inputs, generation_config=config)
        return self._tokenizer.decode(keluaran[0][panjang_masukan:], skip_special_tokens=True).strip()
