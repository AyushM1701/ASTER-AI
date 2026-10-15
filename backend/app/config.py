import re
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.paths import install_root

ROOT = install_root()


class Settings(BaseSettings):
    # The optional teaching profile is separate from the installed medicine/model
    # profile. Explicit .env values and process variables retain precedence.
    model_config = SettingsConfigDict(
        env_file=(ROOT / "configs/teaching.env", ROOT / ".env"), extra="ignore"
    )
    app_env: str = "local"
    workspace_path: Path = ROOT / "data/workspaces/education.sqlite3"
    enable_research_search: bool = True
    answer_mode: str = "extractive"
    retrieval_backend: str = "lexical"
    semantic_min_similarity: float = Field(0.52, ge=0, le=1)
    strict_source_grounding: bool = True
    ollama_base_url: str = "http://127.0.0.1:11434"
    text_model: str = "llama3:8b"
    vision_model: str = "qwen3-vl:2b-instruct"
    enable_general_chat: bool = False
    enable_educational_model_knowledge: bool = False
    enable_teaching: bool = False
    enable_mds_pipeline: bool = True
    mds_synthesis_mode: str = "off"
    enable_patient_information: bool = True
    patient_release_path: Path = (
        ROOT / "data/references/patient/releases/aster-patient-v1-2026-10-10"
    )
    teaching_release_path: Path = ROOT / "data/references/mbbs/releases/aster-mbbs-v1-2026-10-08"
    teaching_backend: str = "lexical"
    teaching_index_path: Path = ROOT / "data/indexes/mbbs_v1"
    teaching_explanations_path: Path = ROOT / "data/references/mbbs/explanations/v1.json"
    teaching_explanations_sha256: str = ""
    tesseract_cmd: str = ""
    enable_handwriting_ocr: bool = False
    max_upload_bytes: int = Field(10_485_760, ge=1024, le=20_971_520)
    max_paper_pages: int = Field(30, ge=1, le=100)
    max_paper_characters: int = Field(240000, ge=1000, le=500000)
    paper_parse_timeout_seconds: int = Field(15, ge=1, le=60)
    max_image_pixels: int = Field(20_000_000, ge=1000, le=40_000_000)
    max_active_sessions: int = Field(20, ge=1, le=100)
    session_ttl_seconds: int = Field(1800, ge=1, le=7200)
    session_hard_ttl_seconds: int = Field(7200, ge=1, le=86400)
    max_documents_per_session: int = Field(5, ge=1, le=20)
    max_session_bytes: int = Field(31_457_280, ge=1024, le=104_857_600)
    max_queue_size: int = Field(4, ge=0, le=10)
    inference_timeout_seconds: int = Field(180, ge=1, le=300)
    ocr_timeout_seconds: int = Field(30, ge=1, le=60)
    corpus_path: Path = ROOT / "data/references/normalized/seed.jsonl"
    source_register: Path = ROOT / "configs/sources.yaml"
    chroma_path: Path = ROOT / "data/indexes/reference_v1"
    embedding_path: Path = ROOT / "data/models/minilm"
    reference_collection: str = "medical_reference_v1"
    enable_secondary_references: bool = False
    secondary_reference_path: Path = (
        ROOT / "data/references/secondary/aster-secondary-v1-r2-2026-10-07"
    )
    secondary_manifest_sha256: str = ""
    enable_xray: bool = False
    xray_manifest: Path = ROOT / "configs/xray_assets.yaml"
    xray_weights_manifest: Path = ROOT / "configs/xray_weights.json"
    # Grounded answer engine (signed library packs + NLI claim verification).
    # "legacy" keeps the earlier extractive teaching pipeline as the chat path.
    answer_engine: str = "legacy"
    enable_library: bool = True
    library_root: Path = ROOT / "data/library/installed"
    nli_model_path: Path = ROOT / "data/models/nli-deberta-v3-xsmall"
    rerank_model_path: Path = ROOT / "data/models/medcpt-cross-encoder"
    model_keep_alive: str = "30m"
    enable_xray_uploads: bool = False
    library_update_url: str = "https://github.com/AyushM1701/ASTER-AI/releases/latest/download/library-latest.json"
    xray_gates_config: Path = ROOT / "configs/xray_gates.json"
    xray_weights_dir: Path = ROOT / "data/models/xray"

    @field_validator("answer_engine")
    @classmethod
    def engine(cls, value):
        if value not in {"legacy", "grounded"}:
            raise ValueError("Choose legacy or grounded")
        return value

    @field_validator("model_keep_alive")
    @classmethod
    def keep_alive(cls, value):
        if not (value in {"0", "-1"} or re.fullmatch(r"\d{1,4}[smh]", value)):
            raise ValueError("keep_alive must look like 30m")
        return value

    @field_validator("ollama_base_url")
    @classmethod
    def local_url(cls, value):
        url = urlsplit(value)
        if (
            url.scheme != "http"
            or url.hostname not in {"127.0.0.1", "localhost", "::1"}
            or url.username
            or url.password
            or url.query
            or url.fragment
            or url.path not in {"", "/"}
        ):
            raise ValueError("Ollama must use a loopback HTTP URL")
        return value.rstrip("/")

    @field_validator("answer_mode")
    @classmethod
    def mode(cls, value):
        if value not in {"extractive", "ollama"}:
            raise ValueError("Choose extractive or ollama")
        return value

    @field_validator("retrieval_backend")
    @classmethod
    def backend(cls, value):
        if value not in {"lexical", "chroma", "hybrid"}:
            raise ValueError("Choose lexical, chroma or hybrid")
        return value

    @field_validator("teaching_backend")
    @classmethod
    def teaching_mode(cls, value):
        if value not in {"lexical", "hybrid"}:
            raise ValueError("Teaching search must be lexical or hybrid")
        return value

    @field_validator("mds_synthesis_mode")
    @classmethod
    def synthesis_mode(cls, value):
        if value not in {"off", "shadow"}:
            raise ValueError("MDS synthesis must be off or shadow; unvalidated drafts cannot be displayed")
        return value

    @field_validator(
        "workspace_path",
        "corpus_path",
        "source_register",
        "teaching_release_path",
        "patient_release_path",
        "teaching_index_path",
        "teaching_explanations_path",
        "secondary_reference_path",
        "chroma_path",
        "embedding_path",
        "xray_manifest",
        "xray_weights_manifest",
        "library_root",
        "nli_model_path",
        "rerank_model_path",
        "xray_gates_config",
        "xray_weights_dir",
    )
    @classmethod
    def absolute_path(cls, value):
        return value if value.is_absolute() else (ROOT / value).resolve()
