"""Biomedical cross-encoder reranking (NCBI MedCPT, int8 ONNX)."""
import threading
from pathlib import Path

import numpy as np


class CrossEncoderReranker:
    def __init__(self, model_dir, threads=4):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_dir = Path(model_dir)
        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=384, strategy="only_second")
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.log_severity_level = 3
        self.session = ort.InferenceSession(str(model_dir / "onnx" / "model_int8.onnx"), options,
                                            providers=["CPUExecutionProvider"])
        self.lock = threading.Lock()

    def scores(self, query, passages, batch=16):
        out = []
        for start in range(0, len(passages), batch):
            encoded = self.tokenizer.encode_batch([(query, p) for p in passages[start:start + batch]])
            length = max(len(e.ids) for e in encoded)
            ids = np.array([e.ids + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
            mask = np.array([e.attention_mask + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
            types = np.array([e.type_ids + [0] * (length - len(e.ids)) for e in encoded], dtype=np.int64)
            with self.lock:
                logits = self.session.run(None, {"input_ids": ids, "attention_mask": mask, "token_type_ids": types})[0]
            out.append(logits.reshape(-1))
        return np.concatenate(out) if out else np.zeros(0)
