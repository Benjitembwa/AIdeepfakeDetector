// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PrismeOpenImageRegistry
/// @notice Registre public de provenance : toute adresse peut enregistrer une image.
/// @dev Les fichiers restent sur IPFS. Une preuve ne peut être révoquée que par
///      l'adresse qui l'a créée. Le premier enregistrement d'un SHA-256 est définitif.
contract PrismeOpenImageRegistry {
    struct ImageRegistration {
        bytes32 mediaId;
        bytes32 metadataSha256;
        uint64 perceptualHash;
        uint64 differenceHash;
        uint64 waveletHash;
        uint64 registeredAt;
        uint64 registeredBlock;
        address publisher;
        bool revoked;
        string imageCid;
        string metadataCid;
    }

    bool public constant registrationOpen = true;
    uint256 public totalRegistrations;

    mapping(bytes32 imageSha256 => ImageRegistration registration) private registrations;

    error InvalidImageHash();
    error InvalidMediaId();
    error InvalidMetadataHash();
    error EmptyImageCid();
    error EmptyMetadataCid();
    error ImageAlreadyRegistered();
    error ImageNotRegistered();
    error ImageAlreadyRevoked();
    error OnlyOriginalPublisher();

    event ImageRegistered(
        bytes32 indexed imageSha256,
        bytes32 indexed mediaId,
        address indexed publisher,
        uint64 registeredAt
    );
    event ImageRevoked(
        bytes32 indexed imageSha256,
        address indexed revokedBy,
        uint64 revokedAt
    );

    function registerImage(
        bytes32 imageSha256,
        uint64 perceptualHash,
        uint64 differenceHash,
        uint64 waveletHash,
        string calldata imageCid,
        string calldata metadataCid,
        bytes32 metadataSha256,
        bytes32 mediaId
    ) external {
        if (imageSha256 == bytes32(0)) revert InvalidImageHash();
        if (mediaId == bytes32(0)) revert InvalidMediaId();
        if (metadataSha256 == bytes32(0)) revert InvalidMetadataHash();
        if (bytes(imageCid).length == 0) revert EmptyImageCid();
        if (bytes(metadataCid).length == 0) revert EmptyMetadataCid();
        if (registrations[imageSha256].registeredAt != 0) revert ImageAlreadyRegistered();

        uint64 timestamp = uint64(block.timestamp);
        ImageRegistration storage registration = registrations[imageSha256];
        registration.mediaId = mediaId;
        registration.metadataSha256 = metadataSha256;
        registration.perceptualHash = perceptualHash;
        registration.differenceHash = differenceHash;
        registration.waveletHash = waveletHash;
        registration.registeredAt = timestamp;
        registration.registeredBlock = uint64(block.number);
        registration.publisher = msg.sender;
        registration.imageCid = imageCid;
        registration.metadataCid = metadataCid;
        unchecked {
            ++totalRegistrations;
        }

        emit ImageRegistered(imageSha256, mediaId, msg.sender, timestamp);
    }

    function revokeImage(bytes32 imageSha256) external {
        ImageRegistration storage registration = registrations[imageSha256];
        if (registration.registeredAt == 0) revert ImageNotRegistered();
        if (registration.revoked) revert ImageAlreadyRevoked();
        if (msg.sender != registration.publisher) revert OnlyOriginalPublisher();
        registration.revoked = true;
        emit ImageRevoked(imageSha256, msg.sender, uint64(block.timestamp));
    }

    function getImage(bytes32 imageSha256) external view returns (ImageRegistration memory) {
        ImageRegistration memory registration = registrations[imageSha256];
        if (registration.registeredAt == 0) revert ImageNotRegistered();
        return registration;
    }

    function exists(bytes32 imageSha256) external view returns (bool) {
        return registrations[imageSha256].registeredAt != 0;
    }

    function isActive(bytes32 imageSha256) external view returns (bool) {
        ImageRegistration storage registration = registrations[imageSha256];
        return registration.registeredAt != 0 && !registration.revoked;
    }
}
