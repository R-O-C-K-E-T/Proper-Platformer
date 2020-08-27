#include "aabb.h"

#include <algorithm>

AABB AABB::mkUnion(const AABB &other) const {
    Vec2d high(std::max(upper.x, other.upper.x),
               std::max(upper.y, other.upper.y));
    Vec2d low(std::min(lower.x, other.lower.x),
              std::min(lower.y, other.lower.y));
    return AABB(high, low);
}

AABB AABB::expand(double radius) const {
    Vec2d high(upper.x + radius, upper.y + radius);
    Vec2d low(lower.x - radius, lower.y - radius);
    return AABB(high, low);
}

double AABB::area() const { return (upper.x - lower.x) * (upper.y - lower.y); }

bool AABB::contains(const AABB &other) const {
    return upper.x >= other.upper.x && upper.y >= other.upper.y &&
           lower.x <= other.lower.x && lower.y <= other.lower.y;
}

bool AABB::intersect(const AABB &other) const {
    /*return (upper.x < other.lower.x || lower.x > other.upper.x) &&
           (upper.y < other.lower.y || lower.y > other.upper.y);*/

    // return !(lower.x > other.upper.x || lower.y > other.upper.y || upper.x <
    // other.lower.x || upper.y < other.lower.y);
    return upper.x > other.lower.x && lower.x < other.upper.x &&
           upper.y > other.lower.y && lower.y < other.upper.y;
}

bool Node::isLeaf() const { return children[0] == nullptr; }

void Node::updateAABB(double margin) {
    if (isLeaf()) {
        outer = inner.expand(margin);
    } else {
        outer = children[0]->outer.mkUnion(children[1]->outer);
    }
}

Node *Node::getSibling() const {
    return parent->children[0] == this ? parent->children[1]
                                       : parent->children[0];
}

Node *AABBTree::add(const AABB &aabb) {
    Node *node = new Node();
    node->inner = aabb;
    node->updateAABB(margin);
    addNode(node);
    return node;
}

void AABBTree::addNode(Node *node) {
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
            (node->parent->children[0] == node ? node->parent->children[0]
                                               : node->parent->children[1]) =
                newParent;
        }

        newParent->parent = node->parent;
        newNode->parent = node->parent = newParent;

        newParent->children[0] = node;
        newParent->children[1] = newNode;

        newParent->updateAABB(margin);
    } else {
        const AABB aabb0 = node->children[0]->outer;
        const AABB aabb1 = node->children[1]->outer;

        const double areaDiff0 =
            aabb0.mkUnion(newNode->outer).area() - aabb0.area();
        const double areaDiff1 =
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
            node->updateAABB(margin);
            addNode(node);
        }
        invalidNodes.clear();
    }
}

void clearChildren(Node *node) {
    node->visited = false;
    if (!node->isLeaf()) {
        clearChildren(node->children[0]);
        clearChildren(node->children[1]);
    }
}

void AABBTree::crossChildren(Node *node) {
    if (!node->visited) {
        findPairs(node->children[0], node->children[1]);
        node->visited = true;
    }
}

void AABBTree::findPairs(Node *n0, Node *n1) {
    if (n0->isLeaf()) {
        if (n1->isLeaf()) {
            if (n0->inner.intersect(n1->inner)) {
                pairs.emplace_back(n0, n1);
            }
        } else {
            crossChildren(n1);
            if (n0->inner.intersect(n1->outer)) {
                findPairs(n0, n1->children[0]);
                findPairs(n0, n1->children[1]);
            }
        }
    } else {
        if (n1->isLeaf()) {
            crossChildren(n0);
            if (n0->outer.intersect(n1->inner)) {
                findPairs(n0->children[0], n1);
                findPairs(n0->children[1], n1);
            }
        } else {
            crossChildren(n0);
            crossChildren(n1);
            if (n0->outer.intersect(n1->outer)) {
                findPairs(n0->children[0], n1->children[0]);
                findPairs(n0->children[0], n1->children[1]);
                findPairs(n0->children[1], n1->children[0]);
                findPairs(n0->children[1], n1->children[1]);
            }
        }
    }
}

const std::vector<std::pair<Node *, Node *>> AABBTree::computePairs() {
    pairs.clear();

    if (root == nullptr || root->isLeaf()) return pairs;

    clearChildren(root);

    findPairs(root->children[0], root->children[1]);

    return pairs;
}
