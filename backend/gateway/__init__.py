"""External Services Gateway: Ollama, Cloudinary, and OpenFoodFacts."""

from backend.gateway.external import ExternalServicesGateway, compress_image_for_ai

__all__ = ["ExternalServicesGateway", "compress_image_for_ai"]
