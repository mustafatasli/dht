#include <stdio.h>
#include <malloc.h>
#include <math.h>

#include "incl.h"

Node *NodeHashTable[HASH_SIZE];

Node *newNode(int id) 
{ 
  Node *n;

  if (!(n = (Node *)calloc(1, sizeof(Node))))
    panic("allocNode: memory alloc. error\n");
  n->id = id;

  return n;
}


/* add node n ad the head of the list */
Node *addToList(Node *head, Node *n)
{
  n->next = head;
  return n;
}

Node *removeFromList(Node *head, Node *n)
{
  Node *n1;

  if (n == head)
    return n->next;

  for (n1 = head; ((n1->next != n) && n1); n1 = n1->next) 
    n1 = n1->next;

  if (!n1)
    panic("removeFromList: node not found\n");

  n1->next = n->next;
  return head;
}


void initNodeHashTable()
{
  int i;

  for (i = 0; i < HASH_SIZE; i++)
    NodeHashTable[i] = NULL;
}

Node *addNode(int id)
{
  Node *n = newNode(id);
  
  NodeHashTable[id % HASH_SIZE] = 
    addToList(NodeHashTable[id % HASH_SIZE], n);
}

void deleteNode(Node *n)
{

  freeDocList(n);

  NodeHashTable[n->id % HASH_SIZE] = 
    removeFromList(NodeHashTable[n->id % HASH_SIZE], n);
  free(n); 
}


Node *getNode(int id)
{
  Node *n = NodeHashTable[id % HASH_SIZE];

  if (id == -1)
    return NULL;

  for (; n; n = n->next)
    if (n->id == id)
      return n;

  return NULL;
}


int getRandomActiveNodeId()
{
  int i, cnt = 0, idx;

  idx = unifRand(0, HASH_SIZE);

  for (i = idx; i < HASH_SIZE; i++)
    if (NodeHashTable[i] && NodeHashTable[i]->status == PRESENT)
      return (NodeHashTable[i])->id;
  
  for (i = idx; i; i--)
    if (NodeHashTable[i] && NodeHashTable[i]->status == PRESENT)
      return (NodeHashTable[i])->id;

  return -1;
}



int getRandomNodeId()
{
  int i;

  /* check whether there hash  is empty -- probably we should just 
   * maintain # of nodes in the network for easy check...
   */
  for (i = 0; i < HASH_SIZE; i++)
    if (NodeHashTable[i])
      break;

  if (i == HASH_SIZE)
    /* hash empty */
    return -1;

  while (1) {
    i = unifRand(0, HASH_SIZE - 1);
    if (NodeHashTable[i])
      return (NodeHashTable[i])->id;
  }
  return -1;
}


/*******************************************************/
/*      update node state
/*******************************************************/

void updateNodeState(Node *n, int id)
{
  int i;

  for (i = 0; i < NUM_BITS; i++) {
    if (id == fingerStart(n, i) || 
	between(id, fingerStart(n, i), n->finger[i], NUM_BITS)) {
      if (i == 0)
	n->finger[0] = n->successor = id;
      else
	n->finger[i] = id;
    }
  }

  if (n->predecessor == n->id || between(id, n->predecessor, n->id, NUM_BITS)) 
    n->predecessor = id;

  updateDocList(n);
}


int printNodeInfo(Node *n)
{
  Document *doc;
  int  i;

  if (n->status == ABSENT)
    return;

  if (n->id == n->successor && n->id == n->predecessor)
    printf("o");

  printf("Node = %d | ", n->id);

  for (i = 0; i < NUM_BITS; i++) {
    printf("<%d:%d> ", fingerStart(n, i), n->finger[i]);
  }
  printf("   predecessor = %d\n", n->predecessor);
  printf("\n");
  
  printf("   doc list: ");
  for (doc = n->docList->head; doc; doc = doc->next)
    printf("%d, ", doc->id);
  printf("\n");
}

void printAllNodesInfo()
{
  int i;
  Node *n;

  printf("---------\n");

  for (i = 0; i < HASH_SIZE; i++) {
    for (n = NodeHashTable[i]; n; n = n->next)
      printNodeInfo(n);
  }
}


void faultyNode(Node *n, int *dummy)
{
  int i;
  Node *n1;

  for (i = 0; i < HASH_SIZE; i++) {
    for (n1 = NodeHashTable[i]; n1; n1 = n1->next) {
      if (n != n1)
	deleteRefFromTables(n1, n->id);
    }
  }
  deleteNode(n);
}

