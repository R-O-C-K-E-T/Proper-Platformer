#pragma once

#include <cmath>
#include <vector>
#include <memory>

#include "vector.h"

class AABBTree;

struct AABB {
   Vec2 upper;
   Vec2 lower;
   
   AABB() : upper(Vec2(NAN, NAN)), lower(Vec2(NAN, NAN)) {}
   AABB(const Vec2& upper, const Vec2& lower) : upper(upper), lower(lower) {}

   AABB mkUnion(const AABB& other) const;
   AABB expand(float_type radius) const;
   float_type area() const { return (upper.x - lower.x) * (upper.y - lower.y); }
   bool contains(const AABB& other) const;
   bool intersect(const AABB& other) const;
};

std::ostream& operator<<(std::ostream & Str, const AABB& v);

class Node {
   friend AABBTree;

   public:
      Node() : parent(nullptr), children{nullptr, nullptr} {};
      virtual ~Node();
      
      Node* getParent() { return parent; }
      Node** getChildren() { return children; }

      AABB getInner() const { return inner; }
      AABB getOuter() const { return outer; }

      bool isLeaf() const { return children[0] == nullptr; }
   
   protected:
      AABB inner;
      AABB outer;

      // Only to be called by AABBTree
      virtual void updateAABB(const float_type margin);

   private:
      Node *parent;
      Node *children[2];

      Node(const Node&) = delete;
      Node& operator=(const Node&) = delete;
      Node(Node&&) = delete;
      Node& operator=(Node&&) = delete;

      Node* getSibling();
};

class AABBTree {
   private:
      std::vector<Node*> invalidNodes;
      std::vector<std::pair<Node*,Node*>> pairs;

      Node *root;

      AABBTree(const AABBTree&) = delete;
      AABBTree& operator=(const AABBTree&) = delete;
      AABBTree(AABBTree&&) = delete;
      AABBTree& operator=(AABBTree&&) = delete;

      void insertNode(Node*, Node*);
      void findInvalid(Node*);
      void findPairs(Node*, Node*);
      void findAllPairs(Node*);
      void findPairsForLeaf(Node* leaf, Node* branch);

   public:
      const float_type margin;

      AABBTree(float_type margin) : root(nullptr), margin(margin) {}

      Node* getRoot() { return root; }

      Node* add(const AABB& aabb);
      void addNode(Node *node);

      //void remove(AABB aabb);
      void removeNode(Node *node);

      const std::vector<std::pair<Node*,Node*>>& computePairs();

      void update();
};