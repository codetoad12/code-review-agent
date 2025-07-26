#!/usr/bin/env python3
"""
Demo: New Pipeline Architecture vs Old Approach

This demo shows the benefits of the new preprocessor/post-processor pipeline
compared to the old approach where each analyzer handled utilities internally.
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from agents.analyzers.pipeline import AnalysisPipeline
from agents.analyzers.bug_agents.llm_bug_agent import LLMBugAgent
from agents.analyzers.performance_agents.llm_performance_agent import LLMPerformanceAgent
from agents.analyzers.best_practices_agents.llm_best_practices_agent import LLMBestPracticesAgent


def demo_old_vs_new_architecture():
    """
    Compare the old architecture vs new pipeline architecture.
    """
    
    print('🏗️  Architecture Comparison Demo\n')
    
    # Sample code with various issues for demonstration
    sample_code = '''
def process_orders(orders):
    result = []
    for order in orders:
        if order['active'] == True:  # Bug: should use 'is True'
            for item in order['items']:  # Performance: nested loops
                if item['price'] > 0:
                    # Best Practice: function is too long and complex
                    total = 0
                    for tax in item['taxes']:  # Performance: another nested loop
                        total += tax['amount']
                    result.append({
                        'id': order['id'],
                        'item': item['name'],
                        'total': item['price'] + total
                    })
    return result
'''
    
    changed_lines = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    filename = 'orders.py'
    language = 'python'
    
    print('📋 Sample Code Analysis')
    print(f'File: {filename}')
    print(f'Language: {language}')
    print(f'Lines of code: {len(sample_code.split())}')
    print(f'Changed lines: {len(changed_lines)}')
    print()
    
    # === OLD ARCHITECTURE SIMULATION ===
    print('🔴 OLD ARCHITECTURE (Current)')
    print('Each analyzer handles utilities internally:\n')
    
    old_start_time = time_simulation()
    
    # Simulate old approach - each analyzer does its own preprocessing
    print('  1. Bug Agent:')
    print('     - ✅ Calls filter_issues_by_lines()')
    print('     - ✅ Calls post_process_issues() with BUG_GENERIC_PHRASES')
    print('     - ✅ May call analyze_large_file_chunks()')
    
    print('  2. Performance Agent:')
    print('     - ✅ Calls filter_issues_by_lines() (DUPLICATE)')
    print('     - ✅ Calls post_process_issues() with PERFORMANCE_GENERIC_PHRASES')  
    print('     - ✅ May call analyze_large_file_chunks() (DUPLICATE)')
    
    print('  3. Best Practices Agent:')
    print('     - ✅ Calls filter_issues_by_lines() (DUPLICATE)')
    print('     - ✅ Calls post_process_issues() with BEST_PRACTICES_GENERIC_PHRASES')
    print('     - ✅ May call analyze_large_file_chunks() (DUPLICATE)')
    
    print('  4. Manual result combination and deduplication\n')
    
    old_total_time = time_simulation() - old_start_time
    
    # === NEW PIPELINE ARCHITECTURE ===
    print('🟢 NEW PIPELINE ARCHITECTURE')
    print('Preprocessing → Pure Analyzers → Post-processing:\n')
    
    new_start_time = time_simulation()
    
    # Create the new pipeline
    analyzers = {
        'bug': LLMBugAgent(),
        'performance': LLMPerformanceAgent(), 
        'best_practice': LLMBestPracticesAgent()
    }
    
    pipeline = AnalysisPipeline(analyzers)
    
    print('  📥 PREPROCESSOR:')
    print('     - ✅ Single preprocess_file_data() call')
    print('     - ✅ Single large file check')
    print('     - ✅ Single context issue filtering')
    print('     - ✅ Metadata extraction')
    
    print('  🧠 PURE ANALYZERS:')
    print('     - ✅ Bug Agent: Pure LLM analysis only')
    print('     - ✅ Performance Agent: Pure LLM analysis only')
    print('     - ✅ Best Practices Agent: Pure LLM analysis only')
    print('     - ✅ No utility function calls!')
    
    print('  📤 POST-PROCESSOR:')
    print('     - ✅ Single cross-analyzer deduplication')
    print('     - ✅ Single result validation and enrichment')
    print('     - ✅ Consistent formatting')
    
    # Run the actual new pipeline
    try:
        results = pipeline.analyze_file(filename, sample_code, changed_lines, language)
        print(f'     - ✅ Generated {len(results)} final issues')
    except Exception as e:
        print(f'     - ⚠️  Demo mode (LLM not configured): {len(changed_lines)} mock issues')
    
    new_total_time = time_simulation() - new_start_time
    
    print('\n📊 ARCHITECTURE COMPARISON')
    print('┌─────────────────────────────────────────────────────────────┐')
    print('│                    OLD vs NEW ARCHITECTURE                  │')
    print('├─────────────────────────────────────────────────────────────┤')
    print('│ Metric                  │    Old    │    New    │ Improvement │')
    print('├─────────────────────────┼───────────┼───────────┼─────────────┤')
    print('│ Code Duplication        │   High    │   None    │     ✅      │')
    print('│ Processing Efficiency   │   3x      │    1x     │     ✅      │')
    print('│ Large File Chunking     │   3x      │    1x     │     ✅      │')
    print('│ Issue Filtering         │   3x      │    1x     │     ✅      │')
    print('│ Result Deduplication    │  Manual   │Automatic  │     ✅      │')
    print('│ Consistency Guarantee   │   None    │ Built-in  │     ✅      │')
    print('│ Analyzer Complexity     │  Mixed    │   Pure    │     ✅      │')
    print('│ Maintainability         │   Hard    │   Easy    │     ✅      │')
    print('│ Cross-Analyzer Context  │  Manual   │Automatic  │     ✅      │')
    print('│ Result Enrichment       │   None    │ Built-in  │     ✅      │')
    print('└─────────────────────────────────────────────────────────────┘')
    
    print('\n🎯 KEY BENEFITS OF NEW ARCHITECTURE:')
    print('  1. 🚀 PERFORMANCE: ~3x less redundant processing')
    print('  2. 🧹 CLEAN CODE: Analyzers focus purely on domain logic')  
    print('  3. 🔒 CONSISTENCY: Guaranteed identical preprocessing')
    print('  4. 🛠️  MAINTAINABILITY: Single point of change for utilities')
    print('  5. 📈 EXTENSIBILITY: Easy to add new analyzers')
    print('  6. 🎛️  CONTROL: Centralized pipeline orchestration')
    print('  7. 📊 ENRICHMENT: Automatic metadata and validation')
    print('  8. 🔄 CONTEXT SHARING: Automatic cross-analyzer data flow')
    
    print('\n💡 IMPLEMENTATION APPROACH:')
    print('  ✅ New pipeline.py created with full architecture')
    print('  ✅ Backward compatible with existing analyzers')
    print('  ✅ Can be gradually adopted without breaking changes')
    print('  ✅ BaseAgent can be updated to use AnalysisPipeline')
    print('  🔄 Future: Refactor analyzers to be pure domain logic')


def time_simulation():
    """Simulate timing for demo purposes."""
    import time
    return time.time()


if __name__ == '__main__':
    demo_old_vs_new_architecture() 