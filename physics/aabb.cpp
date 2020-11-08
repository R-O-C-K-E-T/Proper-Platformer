#include "aabb.h"

#include <algorithm>
#include <functional>

Node::~Node() {}

AABB AABB::mkUnion(const AABB &other) const {
    Vec2 high(std::max(upper.x, other.upper.x),
               std::max(upper.y, other.upper.y));
    Vec2 low(std::min(lower.x, other.lower.x),
              std::min(lower.y, other.lower.y));
    return AABB(high, low);
}

AABB AABB::expand(float_type radius) const {
    Vec2 high(upper.x + radius, upper.y + radius);
    Vec2 low(lower.x - radius, lower.y - radius);
    return AABB(high, low);
}

bool AABB::contains(const AABB &other) const {
    return upper.x >= other.upper.x && upper.y >= other.upper.y &&
           lower.x <= other.lower.x && lower.y <= other.lower.y;
}

bool AABB::intersect(const AABB &other) const {
    return upper.x > other.lower.x && lower.x < other.upper.x &&
           upper.y > other.lower.y && lower.y < other.upper.y;
}

std::ostream& operator<<(std::ostream & Str, const AABB& v) {
   return Str << v.lower << "-" << v.upper;
}

void Node::updateAABB(const float_type margin) {
    if (isLeaf()) {
        outer = inner.expand(margin);
    } else {
        outer = children[0]->outer.mkUnion(children[1]->outer);
    }
}

Node* Node::getSibling() {
    return parent->children[0] == this ? parent->children[1]
                                       : parent->children[0];
}

Node *AABBTree::add(const AABB &aabb) {
    Node *node = new Node();
    node->inner = aabb;
    addNode(node);
    return node;
}

void AABBTree::addNode(Node *node) {
    node->updateAABB(margin);
    if (root == nullptr) {
        root = node;
    } else {
        insertNode(root, node);
    }
}

void AABBTree::insertNode(Node *node, Node *newNode) {
    if (node->isLeaf()) {
        Node *newParent = new Node();

        if (node == root) {
            root = newParent;
        } else {
            (node->parent->children[0] == node ? 
            node->parent->children[0] : node->parent->children[1]) = newParent;
        }

        newParent->parent = node->parent;
        newNode->parent = node->parent = newParent;

        newParent->children[0] = node;
        newParent->children[1] = newNode;

        newParent->updateAABB(margin);
    } else {
        const AABB aabb0 = node->children[0]->outer;
        const AABB aabb1 = node->children[1]->outer;

        const float_type areaDiff0 =
            aabb0.mkUnion(newNode->outer).area() - aabb0.area();
        const float_type areaDiff1 =
            aabb1.mkUnion(newNode->outer).area() - aabb1.area();

        if (areaDiff0 < areaDiff1) {
            insertNode(node->children[0], newNode);
        } else {
            insertNode(node->children[1], newNode);
        }

        node->updateAABB(margin);
    }
}

void AABBTree::removeNode(Node *node) {
    // Node must be leaf
    if (node == root) {
        root = nullptr;
    } else {
        Node *parent = node->parent;
        Node *sibling = node->getSibling();

        if (parent == root) {
            root = sibling;
            sibling->parent = nullptr;
        } else {
            sibling->parent = parent->parent;

            (parent->parent->children[0] == parent
                 ? parent->parent->children[0]
                 : parent->parent->children[1]) = sibling;
            delete parent;
        }
    }
}

void AABBTree::findInvalid(Node *node) {
    if (node->isLeaf()) {
        if (!node->outer.contains(node->inner)) {
            invalidNodes.push_back(node);
        }
    } else {
        findInvalid(node->children[0]);
        findInvalid(node->children[1]);
    }
}

void AABBTree::update() {
    if (root == nullptr) return;

    if (root->isLeaf()) {
        root->updateAABB(margin);
    } else {
        findInvalid(root);
        for (Node *node : invalidNodes) {
            removeNode(node);
            addNode(node);
        }
        invalidNodes.clear();
    }
}

void AABBTree::findPairsForLeaf(Node* leaf, Node* branch) {
    // Finds all collisions from a given leaf onto a node which may be a leaf
    if (branch->isLeaf()) {
        if (branch->inner.intersect(leaf->inner)) {
            pairs.emplace_back(leaf, branch);
        }
    } else {
        if (branch->outer.intersect(leaf->inner)) {
            findPairsForLeaf(leaf, branch->children[0]);
            findPairsForLeaf(leaf, branch->children[1]);
        }
    }
}

void AABBTree::findPairs(Node* n0, Node* n1) {
    // Finds all collisions across the two given nodes
    if (n0->isLeaf()) {
        if (n1->isLeaf()) {
            if (n0->inner.intersect(n1->inner)) {
                pairs.emplace_back(n0, n1);
            }
        } else {
            if (n0->inner.intersect(n1->outer)) {
                findPairsForLeaf(n0, n1->children[0]);
                findPairsForLeaf(n0, n1->children[1]);
            }
        }
    } else {
        if (n1->isLeaf()) {
            if (n0->outer.intersect(n1->inner)) {
                findPairsForLeaf(n1, n0->children[0]);
                findPairsForLeaf(n1, n0->children[1]);
            }
        } else {
            if (n0->outer.intersect(n1->outer)) {
                findPairs(n0->children[0], n1->children[0]);
                findPairs(n0->children[0], n1->children[1]);
                findPairs(n0->children[1], n1->children[0]);
                findPairs(n0->children[1], n1->children[1]);
            }
        }
    }
}

void AABBTree::findAllPairs(Node* node) {
    if (!node->isLeaf()) {
        findPairs(node->children[0], node->children[1]);

        findAllPairs(node->children[0]);
        findAllPairs(node->children[1]);
    }
}

const std::vector<std::pair<Node *, Node *>>& AABBTree::computePairs() {
    pairs.clear();

    if (root == nullptr) return pairs;
    findAllPairs(root);
    return pairs;
}
