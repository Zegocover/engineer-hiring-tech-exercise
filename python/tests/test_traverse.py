import pytest
import asyncio

from crawler.traverse import PooledTraverse


@pytest.mark.asyncio
async def test_single_node_graph_with_single_worker():
    async def visit(_):
        await asyncio.sleep(0)
        return []

    traverse = PooledTraverse(root=1, visit=visit, workers=1)
    visited = await traverse.run()

    assert sorted(visited) == [1]


@pytest.mark.asyncio
async def test_single_node_graph_with_multiple_workers():
    async def visit(_):
        await asyncio.sleep(0)
        return []

    traverse = PooledTraverse(root=1, visit=visit, workers=1)
    visited = await traverse.run()

    assert sorted(visited) == [1]


@pytest.mark.asyncio
async def test_traverse_graph_with_single_worker():
    async def visit(node):
        adjacency = {
            1: [1, 2, 3],
            2: [4, 1],
            3: [5, 2],
            4: [4],
            5: [],
        }

        await asyncio.sleep(0)

        return adjacency.get(node, [])

    traverse = PooledTraverse(root=1, visit=visit, workers=1)
    visited = await traverse.run()

    assert sorted(visited) == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_traverse_graph_with_multiple_workers():
    async def visit(node):
        adjacency = {
            "A": ["A", "B", "C"],
            "B": ["D", "A"],
            "C": ["E", "B"],
            "D": ["D"],
            "E": [],
        }

        await asyncio.sleep(0)

        return adjacency.get(node, [])

    traverse = PooledTraverse(root="A", visit=visit, workers=5)
    visited = await traverse.run()

    assert sorted(visited) == ["A", "B", "C", "D", "E"]


@pytest.mark.asyncio
async def test_traverse_halts_on_exception_single_worker():
    async def visit(node):
        adjacency = {
            1: [1, 2, 3],
            2: [4, 1],
            3: [5, 2],
            4: [4],
            5: [],
        }

        if node == 3:
            raise RuntimeError("Simulated Exception")

        await asyncio.sleep(0)

        return adjacency.get(node, [])

    with pytest.raises(ExceptionGroup) as ctx:
        await PooledTraverse(root=1, visit=visit, workers=1).run()

    assert len(ctx.value.exceptions) == 1
    assert isinstance(ctx.value.exceptions[0], RuntimeError)


@pytest.mark.asyncio
async def test_traverse_halts_on_exception_multiple_workers():
    async def visit(node):
        adjacency = {
            1: [1, 2, 3],
            2: [4, 1],
            3: [5, 2],
            4: [4],
            5: [],
        }

        if node == 3:
            raise RuntimeError("Simulated Exception")

        await asyncio.sleep(0)

        return adjacency.get(node, [])

    with pytest.raises(ExceptionGroup) as ctx:
        await PooledTraverse(root=1, visit=visit, workers=5).run()

    assert len(ctx.value.exceptions) == 1
    assert isinstance(ctx.value.exceptions[0], RuntimeError)
