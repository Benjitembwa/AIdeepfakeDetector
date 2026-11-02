// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PrismeImageRegistry
/// @notice Registre de provenance des images publié sur Base Sepolia.
/// @dev Le fichier image reste sur IPFS. Le contrat conserve ses empreintes,
///      ses CID et l'identité technique du média qui l'a enregistré.
contract PrismeImageRegistry {
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

    address public owner;
    uint256 public totalRegistrations;

    mapping(address publisher => bool authorized) public authorizedPublishers;
    mapping(bytes32 imageSha256 => ImageRegistration registration) private registrations;

    error OnlyOwner();
    error UnauthorizedPublisher();
    error InvalidAddress();
    error InvalidImageHash();
    error InvalidMediaId();
    error InvalidMetadataHash();
    error EmptyImageCid();
    error EmptyMetadataCid();
    error ImageAlreadyRegistered();
    error ImageNotRegistered();
    error ImageAlreadyRevoked();
    error CannotRevokeImage();

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event PublisherAuthorizationChanged(address indexed publisher, bool authorized);
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

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    modifier onlyAuthorizedPublisher() {
        if (!authorizedPublishers[msg.sender]) revert UnauthorizedPublisher();
        _;
    }

    constructor() {
        owner = msg.sender;
        authorizedPublishers[msg.sender] = true;
        emit OwnershipTransferred(address(0), msg.sender);
        emit PublisherAuthorizationChanged(msg.sender, true);
    }

    /// @notice Autorise ou retire une adresse capable d'enregistrer des images.
    function setPublisher(address publisher, bool authorized) external onlyOwner {
        if (publisher == address(0)) revert InvalidAddress();
        authorizedPublishers[publisher] = authorized;
        emit PublisherAuthorizationChanged(publisher, authorized);
    }

    /// @notice Transfère l'administration du registre.
    /// @dev L'ancien propriétaire reste éditeur jusqu'à un éventuel setPublisher(false).
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert InvalidAddress();
        address previousOwner = owner;
        owner = newOwner;
        authorizedPublishers[newOwner] = true;
        emit PublisherAuthorizationChanged(newOwner, true);
        emit OwnershipTransferred(previousOwner, newOwner);
    }

    /// @notice Enregistre définitivement les preuves d'une image.
    /// @param imageSha256 SHA-256 exact du fichier image, encodé sur 32 octets.
    /// @param perceptualHash pHash 64 bits calculé par Prisme.
    /// @param differenceHash dHash 64 bits calculé par Prisme.
    /// @param waveletHash wHash 64 bits calculé par Prisme.
    /// @param imageCid CID IPFS du fichier image.
    /// @param metadataCid CID IPFS du document JSON de métadonnées.
    /// @param metadataSha256 SHA-256 du document JSON canonique.
    /// @param mediaId Identifiant pseudonymisé du média partenaire sur 32 octets.
    function registerImage(
        bytes32 imageSha256,
        uint64 perceptualHash,
        uint64 differenceHash,
        uint64 waveletHash,
        string calldata imageCid,
        string calldata metadataCid,
        bytes32 metadataSha256,
        bytes32 mediaId
    ) external onlyAuthorizedPublisher {
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

    /// @notice Révoque un enregistrement sans effacer son historique.
    function revokeImage(bytes32 imageSha256) external {
        ImageRegistration storage registration = registrations[imageSha256];
        if (registration.registeredAt == 0) revert ImageNotRegistered();
        if (registration.revoked) revert ImageAlreadyRevoked();
        if (msg.sender != owner && msg.sender != registration.publisher) {
            revert CannotRevokeImage();
        }
        registration.revoked = true;
        emit ImageRevoked(imageSha256, msg.sender, uint64(block.timestamp));
    }

    /// @notice Retourne toutes les informations enregistrées pour un SHA-256.
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
