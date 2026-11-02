import hashlib
import io
from dataclasses import dataclass

import cv2
import imagehash
import numpy as np
from PIL import Image

FINGERPRINT_VERSION = 1
HASH_BITS = 64
ORB_DESCRIPTOR_SIZE = 32


@dataclass(frozen=True)
class ImageFingerprint:
    sha256: str
    perceptual_hash: str
    difference_hash: str
    wavelet_hash: str
    orb_keypoints: bytes | None
    orb_descriptors: bytes | None
    orb_descriptor_count: int


@dataclass(frozen=True)
class FingerprintComparison:
    matched_by: str | None
    confidence: float
    perceptual_distance: int | None
    difference_distance: int | None
    wavelet_distance: int | None
    good_matches: int
    inliers: int


def compute_fingerprint(contents: bytes) -> ImageFingerprint:
    with Image.open(io.BytesIO(contents)) as opened:
        rgb = opened.convert("RGB")
        perceptual_hash = str(imagehash.phash(rgb))
        difference_hash = str(imagehash.dhash(rgb))
        wavelet_hash = str(imagehash.whash(rgb))
        grayscale = np.asarray(rgb.convert("L"), dtype=np.uint8)

    height, width = grayscale.shape
    longest = max(height, width)
    if longest > 1600:
        scale = 1600 / longest
        grayscale = cv2.resize(
            grayscale,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    orb = cv2.ORB_create(nfeatures=1200, fastThreshold=12)
    keypoints, descriptors = orb.detectAndCompute(grayscale, None)
    if descriptors is None or not keypoints:
        keypoint_bytes = None
        descriptor_bytes = None
        descriptor_count = 0
    else:
        points = np.asarray([point.pt for point in keypoints], dtype="<f4")
        descriptor_array = np.asarray(descriptors, dtype=np.uint8)
        keypoint_bytes = points.tobytes()
        descriptor_bytes = descriptor_array.tobytes()
        descriptor_count = len(descriptor_array)

    return ImageFingerprint(
        sha256=hashlib.sha256(contents).hexdigest(),
        perceptual_hash=perceptual_hash,
        difference_hash=difference_hash,
        wavelet_hash=wavelet_hash,
        orb_keypoints=keypoint_bytes,
        orb_descriptors=descriptor_bytes,
        orb_descriptor_count=descriptor_count,
    )


def _hash_distance(left: str | None, right: str | None) -> int | None:
    if not left or not right or len(left) != len(right):
        return None
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError:
        return None


def _orb_match(
    query: ImageFingerprint,
    stored_keypoints: bytes | None,
    stored_descriptors: bytes | None,
    stored_count: int | None,
) -> tuple[int, int, float]:
    if (
        not query.orb_keypoints
        or not query.orb_descriptors
        or query.orb_descriptor_count < 4
        or not stored_keypoints
        or not stored_descriptors
        or not stored_count
        or stored_count < 4
    ):
        return 0, 0, 0.0
    try:
        query_points = np.frombuffer(query.orb_keypoints, dtype="<f4").reshape(-1, 2)
        stored_points = np.frombuffer(stored_keypoints, dtype="<f4").reshape(-1, 2)
        query_descriptors = np.frombuffer(query.orb_descriptors, dtype=np.uint8).reshape(
            query.orb_descriptor_count, ORB_DESCRIPTOR_SIZE
        )
        stored_descriptor_array = np.frombuffer(
            stored_descriptors, dtype=np.uint8
        ).reshape(stored_count, ORB_DESCRIPTOR_SIZE)
    except (ValueError, TypeError):
        return 0, 0, 0.0

    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(
        query_descriptors, stored_descriptor_array, k=2
    )
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
    if len(good) < 4:
        return len(good), 0, 0.0
    source = np.float32([query_points[match.queryIdx] for match in good]).reshape(-1, 1, 2)
    target = np.float32([stored_points[match.trainIdx] for match in good]).reshape(-1, 1, 2)
    _, mask = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
    inliers = int(mask.sum()) if mask is not None else 0
    inlier_ratio = inliers / len(good)
    coverage = min(inliers / 30, 1.0)
    return len(good), inliers, 0.55 * inlier_ratio + 0.45 * coverage


def compare_fingerprints(
    query: ImageFingerprint,
    *,
    stored_sha256: str | None,
    stored_perceptual_hash: str | None,
    stored_difference_hash: str | None,
    stored_wavelet_hash: str | None,
    stored_keypoints: bytes | None,
    stored_descriptors: bytes | None,
    stored_descriptor_count: int | None,
) -> FingerprintComparison:
    if stored_sha256 and query.sha256 == stored_sha256:
        return FingerprintComparison("exact", 1.0, 0, 0, 0, 0, 0)

    perceptual_distance = _hash_distance(query.perceptual_hash, stored_perceptual_hash)
    difference_distance = _hash_distance(query.difference_hash, stored_difference_hash)
    wavelet_distance = _hash_distance(query.wavelet_hash, stored_wavelet_hash)
    distances = [perceptual_distance, difference_distance, wavelet_distance]
    weights = [0.5, 0.25, 0.25]
    available = [(distance, weight) for distance, weight in zip(distances, weights) if distance is not None]
    if available:
        total_weight = sum(weight for _, weight in available)
        perceptual_score = sum(
            max(0.0, 1 - distance / HASH_BITS) * weight for distance, weight in available
        ) / total_weight
    else:
        perceptual_score = 0.0

    good_matches, inliers, local_score = _orb_match(
        query, stored_keypoints, stored_descriptors, stored_descriptor_count
    )
    if perceptual_score >= 0.82:
        return FingerprintComparison(
            "perceptual",
            round(perceptual_score, 4),
            perceptual_distance,
            difference_distance,
            wavelet_distance,
            good_matches,
            inliers,
        )
    if good_matches >= 8 and inliers >= 5 and inliers / good_matches >= 0.25:
        return FingerprintComparison(
            "local_features",
            round(local_score, 4),
            perceptual_distance,
            difference_distance,
            wavelet_distance,
            good_matches,
            inliers,
        )
    return FingerprintComparison(
        None,
        round(max(perceptual_score, local_score), 4),
        perceptual_distance,
        difference_distance,
        wavelet_distance,
        good_matches,
        inliers,
    )
