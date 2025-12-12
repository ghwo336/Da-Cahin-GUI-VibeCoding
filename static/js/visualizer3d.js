// 3D Blockchain Visualizer using Three.js

let scene, camera, renderer, controls;
let blockMeshes = [];
let chainLinks = [];
let selectedBlockMesh = null;

// Initialize 3D scene
function init3DVisualizer() {
    const container = document.getElementById('chain-canvas-3d');

    // Clear previous content
    container.innerHTML = '';

    // Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f0f23);

    // Camera setup - fixed top-down view
    camera = new THREE.PerspectiveCamera(
        60,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 25, 0); // Top-down view
    camera.lookAt(0, 0, 0);

    // Renderer setup
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 5);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    const pointLight = new THREE.PointLight(0x667eea, 1, 50);
    pointLight.position.set(0, 5, 0);
    scene.add(pointLight);

    // Mouse controls
    setupMouseControls(container);

    // Handle window resize
    window.addEventListener('resize', onWindowResize, false);

    // Start animation loop
    animate();
}

function setupMouseControls(container) {
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let cameraOffset = { x: 0, z: 0 };

    container.addEventListener('mousedown', (e) => {
        isDragging = true;
        previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    container.addEventListener('mousemove', (e) => {
        if (isDragging) {
            const deltaX = e.clientX - previousMousePosition.x;

            // Only horizontal movement (left-right)
            cameraOffset.x -= deltaX * 0.05;

            // Update camera position - maintain top-down view
            camera.position.set(cameraOffset.x, 25, cameraOffset.z);
            camera.lookAt(cameraOffset.x, 0, cameraOffset.z);

            previousMousePosition = { x: e.clientX, y: e.clientY };
        }
    });

    container.addEventListener('mouseup', (e) => {
        // Only trigger click if not dragged
        if (!isDragging) {
            onBlockClick(e, container);
        }
        isDragging = false;
    });

    container.addEventListener('mouseleave', () => {
        isDragging = false;
    });

    // Click to select block
    container.addEventListener('click', (e) => {
        if (!isDragging) {
            onBlockClick(e, container);
        }
    });

    // Change cursor
    container.style.cursor = 'grab';
    container.addEventListener('mousedown', () => {
        container.style.cursor = 'grabbing';
    });
    container.addEventListener('mouseup', () => {
        container.style.cursor = 'grab';
    });
}

function onBlockClick(event, container) {
    const rect = container.getBoundingClientRect();
    const mouse = new THREE.Vector2();
    mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);

    // Intersect with all children (recursive = true)
    const intersects = raycaster.intersectObjects(blockMeshes, true);

    if (intersects.length > 0) {
        // Find the parent block group
        let clickedObject = intersects[0].object;

        // Traverse up to find the block group
        while (clickedObject.parent && !clickedObject.userData.blockData) {
            clickedObject = clickedObject.parent;
        }

        if (clickedObject.userData.blockData) {
            selectBlock3D(clickedObject);
        }
    }
}

function selectBlock3D(blockMesh) {
    // Open modal with block info
    openBlockModal(blockMesh.userData.blockData);
}

function openBlockModal(block) {
    const modal = document.getElementById('block-modal');
    const container = document.getElementById('modal-block-info');

    const isGenesis = block.height === 0;

    let html = `
        <h2>${isGenesis ? '🌟 Genesis Block' : `Block #${block.height}`}</h2>
        <p><strong>Hash:</strong><br><code>${block.hash}</code></p>
        <p><strong>Previous Hash:</strong><br><code>${block.prev_hash}</code></p>
        <p><strong>Merkle Root:</strong><br><code>${block.merkle_root}</code></p>
        <p><strong>Timestamp:</strong> ${new Date(block.timestamp * 1000).toLocaleString('ko-KR')}</p>
        <p><strong>Nonce:</strong> ${block.nonce}</p>
        <p><strong>Difficulty:</strong> ${block.difficulty || 4}</p>
        <p><strong>Transactions:</strong> ${block.tx_count || 0}개</p>
    `;

    container.innerHTML = html;
    modal.classList.add('active');
}

// Close modal function (called from HTML)
window.closeBlockModal = function() {
    const modal = document.getElementById('block-modal');
    modal.classList.remove('active');
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('block-modal');
    if (event.target === modal) {
        modal.classList.remove('active');
    }
});

async function load3DChain() {
    try {
        const response = await fetch('/api/blockchain');
        const blocks = await response.json();

        if (!blocks || blocks.length === 0) {
            console.warn('No blocks in blockchain');
            return;
        }

        console.log(`Loading ${blocks.length} blocks into 3D visualization`);
        render3DBlocks(blocks);
    } catch (error) {
        console.error('Error loading 3D chain:', error);
    }
}

function render3DBlocks(blocks) {
    // Clear existing blocks and all sprites
    blockMeshes.forEach(mesh => {
        scene.remove(mesh);
        // Remove associated sprite
        if (mesh.userData.sprite) {
            scene.remove(mesh.userData.sprite);
        }
    });
    chainLinks.forEach(link => scene.remove(link));
    blockMeshes = [];
    chainLinks = [];

    const spacing = 10.5; // Space between blocks (1.5x original)

    blocks.forEach((block, index) => {
        // Arrange blocks in a horizontal line
        const x = index * spacing - (blocks.length * spacing) / 2;
        const y = 0;
        const z = 0;

        // Create block mesh with gradient color
        const blockMesh = createBlockMesh(block, x, y, z, index, blocks.length);
        blockMesh.userData.blockData = block;
        blockMesh.userData.index = index;
        scene.add(blockMesh);
        blockMeshes.push(blockMesh);

        // Create link to previous block
        if (index > 0) {
            const prevBlock = blockMeshes[index - 1];
            const link = createLink(
                prevBlock.position,
                blockMesh.position
            );
            scene.add(link);
            chainLinks.push(link);
        }
    });

    // Don't auto-select on load
    // User will click to see block details
}

function createBlockMesh(block, x, y, z, index, totalBlocks) {
    const isGenesis = block.height === 0;

    // Create group to hold cube and edges
    const blockGroup = new THREE.Group();
    blockGroup.position.set(x, y, z);

    // Block geometry - cube (regular square on all sides) - larger size
    const geometry = new THREE.BoxGeometry(6, 6, 6); // perfect cube
    geometry.computeVertexNormals();

    // Beautiful gradient colors (like the original 2D visualizer)
    let color, emissiveColor;
    if (isGenesis) {
        // Genesis block - pink
        color = 0xff69b4; // Hot pink
        emissiveColor = 0xff1493; // Deep pink
    } else {
        // Gradient from purple to blue
        const ratio = index / Math.max(totalBlocks - 1, 1);
        const r = Math.floor(102 + (118 - 102) * ratio);
        const g = Math.floor(126 + (75 - 126) * ratio);
        const b = Math.floor(234 + (162 - 234) * ratio);
        color = (r << 16) | (g << 8) | b;
        emissiveColor = color;
    }

    const material = new THREE.MeshStandardMaterial({
        color: color,
        emissive: emissiveColor,
        emissiveIntensity: 0.4,
        metalness: 0.3,
        roughness: 0.4
    });

    const cube = new THREE.Mesh(geometry, material);
    cube.castShadow = true;
    cube.receiveShadow = true;
    blockGroup.add(cube);

    // Add glowing edges
    const edgesGeometry = new THREE.EdgesGeometry(geometry);
    const edgesMaterial = new THREE.LineBasicMaterial({
        color: isGenesis ? 0xff1493 : 0xffffff, // Deep pink for genesis
        linewidth: 3,
        opacity: 0.8,
        transparent: true
    });
    const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
    blockGroup.add(edges);

    // Add block number as text (sprite)
    const sprite = createTextSprite(`#${block.height}`, isGenesis);
    sprite.position.set(0, 4, 0); // Adjusted for cube
    blockGroup.add(sprite);
    blockGroup.userData.sprite = sprite;

    // Add hash info sprite (smaller)
    const hashSprite = createHashSprite(block.hash.substring(0, 8) + '...', isGenesis);
    hashSprite.position.set(0, -4, 0); // Adjusted for cube
    blockGroup.add(hashSprite);

    // Store the block group data
    blockGroup.userData.blockData = block;

    return blockGroup;
}

function createTextSprite(text, isGenesis = false) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512;
    canvas.height = 128;

    context.fillStyle = isGenesis ? '#ff69b4' : '#ffffff'; // Hot pink for genesis
    context.font = 'bold 40px Arial';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(4, 1, 1);

    return sprite;
}

function createHashSprite(text, isGenesis = false) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512;
    canvas.height = 128;

    context.fillStyle = isGenesis ? '#ffb6c1' : '#aaaaff'; // Light pink for genesis hash
    context.font = '28px monospace';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(3, 0.75, 1);

    return sprite;
}

function createLink(start, end) {
    // Create chain-like link using multiple connected segments - larger and more twisted
    const chainGroup = new THREE.Group();

    // Create chain link geometry (torus shape) - bigger and more links
    const numLinks = 5; // More chain links for better twisting effect
    const linkSpacing = new THREE.Vector3().subVectors(end, start).divideScalar(numLinks);

    for (let i = 0; i < numLinks; i++) {
        const linkPos = new THREE.Vector3()
            .copy(start)
            .add(linkSpacing.clone().multiplyScalar(i + 0.5));

        // Create larger torus (ring) for chain link
        const torusGeometry = new THREE.TorusGeometry(0.6, 0.2, 12, 16); // 2x bigger
        const torusMaterial = new THREE.MeshStandardMaterial({
            color: 0xcccccc,
            metalness: 0.9,
            roughness: 0.1
        });

        const torus = new THREE.Mesh(torusGeometry, torusMaterial);
        torus.position.copy(linkPos);

        // Rotate torus with more variation to create twisted effect
        if (i % 2 === 0) {
            torus.rotation.y = Math.PI / 2;
            torus.rotation.z = Math.PI / 6; // Add twist
        } else {
            torus.rotation.x = Math.PI / 6; // Add twist
        }

        chainGroup.add(torus);
    }

    // Add thicker connecting cylinders between links
    const cylinderGeometry = new THREE.CylinderGeometry(0.15, 0.15, linkSpacing.length(), 8);
    const cylinderMaterial = new THREE.MeshStandardMaterial({
        color: 0xaaaaaa,
        metalness: 0.85,
        roughness: 0.15
    });

    for (let i = 0; i < numLinks - 1; i++) {
        const pos1 = new THREE.Vector3()
            .copy(start)
            .add(linkSpacing.clone().multiplyScalar(i + 0.5));
        const pos2 = new THREE.Vector3()
            .copy(start)
            .add(linkSpacing.clone().multiplyScalar(i + 1.5));

        const cylinder = new THREE.Mesh(cylinderGeometry, cylinderMaterial);
        const midPoint = new THREE.Vector3().addVectors(pos1, pos2).multiplyScalar(0.5);
        cylinder.position.copy(midPoint);

        // Rotate cylinder to connect the links
        const direction = new THREE.Vector3().subVectors(pos2, pos1);
        const axis = new THREE.Vector3(0, 1, 0);
        cylinder.quaternion.setFromUnitVectors(axis, direction.normalize());

        chainGroup.add(cylinder);
    }

    return chainGroup;
}

function animate() {
    requestAnimationFrame(animate);

    // Rotate all blocks
    blockMeshes.forEach((blockGroup) => {
        // Gentle rotation - up and down (X-axis)
        blockGroup.rotation.x += 0.005;
    });

    // Rotate all chain links
    chainLinks.forEach((chainGroup) => {
        // Rotate chains in the same direction as blocks
        chainGroup.rotation.x += 0.005;
    });

    renderer.render(scene, camera);
}

function onWindowResize() {
    const container = document.getElementById('chain-canvas-3d');
    if (container && renderer) {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }
}

// Export functions
window.init3DVisualizer = init3DVisualizer;
window.load3DChain = load3DChain;
