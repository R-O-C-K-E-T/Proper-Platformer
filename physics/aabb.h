#pragma once

#include <cmath>
#include <vector>

#include "vector.h"

struct AABB {
   Vec2d upper;
   Vec2d lower;
   
   AABB() : upper(Vec2d(NAN, NAN)), lower(Vec2d(NAN, NAN)) {}
   AABB(Vec2d upper, Vec2d lower) : upper(upper), lower(lower) {}

   AABB mkUnion(const AABB& other) const;
   AABB expand(double radius) const;
   double area() const;
   bool contains(const AABB& other) const;
   bool intersect(const AABB& other) const;
};

struct Node {
   Node *parent;
   Node *children[2];

   AABB inner;
   AABB outer;

   bool visited = false;

   Node() : parent(nullptr) {
      children[0] = nullptr;
      children[1] = nullptr;
   };

   void updateAABB(double margin);

   bool isLeaf() const;
   Node* getSibling() const;
};

class AABBTree {
   std::vector<Node*> invalidNodes;
   std::vector<std::pair<Node*,Node*>> pairs;

   void insertNode(Node*, Node*);
   void findInvalid(Node*);
   void findPairs(Node*, Node*);
   void crossChildren(Node*);

   public:
      Node *root;
      const double margin;

      AABBTree(double margin) : root(nullptr), margin(margin) {}

      Node* add(const AABB& aabb);
      void addNode(Node *node);

      //void remove(AABB aabb);
      void removeNode(Node *node);

      const std::vector<std::pair<Node*,Node*>> computePairs();

      void update();
};