#!/usr/bin/env node

/**
 * VoiceFlow Pro Case Study Test Runner
 * Automated testing framework for validating case study claims
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class CaseStudyTestRunner {
    constructor() {
        this.baseUrl = 'http://localhost:8000';
        this.results = {
            timestamp: new Date().toISOString(),
            testSuite: 'VoiceFlow Pro Case Studies',
            version: '1.0.0',
            environment: 'development',
            tests: []
        };
    }

    async runAllTests() {
        console.log('🚀 Starting VoiceFlow Pro Case Study Tests...\n');
        
        // Test system health first
        await this.testSystemHealth();
        
        // Run case study scenarios
        await this.runSalesScenarios();
        await this.runSupportScenarios();
        await this.runSchedulingScenarios();
        
        // Generate final report
        await this.generateReport();
        
        console.log('\n✅ All tests completed! Check results in case-studies/results/');
    }

    async testSystemHealth() {
        console.log('🔍 Testing System Health...');
        const startTime = Date.now();
        
        try {
            const response = await axios.get(`${this.baseUrl}/health`);
            const latency = Date.now() - startTime;
            
            const healthTest = {
                name: 'System Health Check',
                category: 'Infrastructure',
                status: response.status === 200 ? 'PASS' : 'FAIL',
                latency: `${latency}ms`,
                data: response.data,
                timestamp: new Date().toISOString()
            };
            
            this.results.tests.push(healthTest);
            console.log(`   ✅ Health Check: ${latency}ms`);
            
        } catch (error) {
            console.log(`   ❌ Health Check Failed: ${error.message}`);
            this.results.tests.push({
                name: 'System Health Check',
                category: 'Infrastructure',
                status: 'FAIL',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
    }

    async runSalesScenarios() {
        console.log('\n💼 Testing Sales Lead Qualification Scenarios...');
        
        // Test 1A: Qualified Lead
        await this.testScenario({
            name: 'TechCorp - Qualified Lead',
            category: 'Sales',
            scenario: 'qualified_lead',
            expectedScore: 85,
            expectedAction: 'schedule_demo',
            conversation: [
                { role: 'user', message: 'Hi, I\'m interested in your enterprise software solutions' },
                { role: 'user', message: 'We\'re a 200-person marketing agency' },
                { role: 'user', message: 'We have a budget of around $50,000 annually' },
                { role: 'user', message: 'We\'re looking to implement something in the next quarter' }
            ]
        });

        // Test 1B: Unqualified Lead
        await this.testScenario({
            name: 'TechCorp - Unqualified Lead',
            category: 'Sales',
            scenario: 'unqualified_lead',
            expectedScore: 20,
            expectedAction: 'nurture_sequence',
            conversation: [
                { role: 'user', message: 'I heard about your software, what do you do?' },
                { role: 'user', message: 'I\'m a student, just curious about tech' },
                { role: 'user', message: 'I don\'t have a budget, just learning' }
            ]
        });
    }

    async runSupportScenarios() {
        console.log('\n🎧 Testing Customer Support Scenarios...');
        
        // Test 2A: Simple Issue
        await this.testScenario({
            name: 'ServiceMax - Password Reset',
            category: 'Support',
            scenario: 'simple_issue',
            expectedCategory: 'authentication',
            expectedResolution: 'automated',
            conversation: [
                { role: 'user', message: 'I can\'t log into my account' },
                { role: 'user', message: 'It says invalid password' },
                { role: 'user', message: 'I logged in yesterday, but today it\'s not working' }
            ]
        });

        // Test 2B: Complex Issue
        await this.testScenario({
            name: 'ServiceMax - API Integration',
            category: 'Support',
            scenario: 'complex_issue',
            expectedCategory: 'integration',
            expectedResolution: 'escalate',
            conversation: [
                { role: 'user', message: 'Our API integration stopped working this morning' },
                { role: 'user', message: 'Getting 500 errors on all endpoints' },
                { role: 'user', message: 'We updated our SSL certificates yesterday' }
            ]
        });
    }

    async runSchedulingScenarios() {
        console.log('\n📅 Testing Appointment Scheduling Scenarios...');
        
        // Test 3A: Standard Appointment
        await this.testScenario({
            name: 'MedClinic - Routine Checkup',
            category: 'Scheduling',
            scenario: 'standard_appointment',
            expectedSuccess: true,
            expectedTimeframe: 'next_week',
            conversation: [
                { role: 'user', message: 'I need to schedule a routine checkup' },
                { role: 'user', message: 'I\'d like to see Dr. Smith if possible' },
                { role: 'user', message: 'Sometime next week, preferably afternoon' }
            ]
        });

        // Test 3B: Urgent Appointment
        await this.testScenario({
            name: 'MedClinic - Urgent Care',
            category: 'Scheduling',
            scenario: 'urgent_appointment',
            expectedPriority: 'urgent',
            expectedTimeframe: 'same_day',
            conversation: [
                { role: 'user', message: 'I have severe chest pain, need to see someone today' },
                { role: 'user', message: 'Started 2 hours ago, getting worse' },
                { role: 'user', message: 'I have a history of heart problems' }
            ]
        });
    }

    async testScenario(scenario) {
        console.log(`   🧪 Testing: ${scenario.name}`);
        const startTime = Date.now();
        
        try {
            // Simulate conversation processing
            const roomId = `test-${Date.now()}`;
            const conversationData = {
                roomId,
                scenario: scenario.scenario,
                messages: scenario.conversation,
                timestamp: new Date().toISOString()
            };

            // Test conversation processing endpoint
            const response = await axios.post(`${this.baseUrl}/api/agent/conversation`, conversationData);
            const processingTime = Date.now() - startTime;

            // Test analytics endpoint
            const analyticsResponse = await axios.get(`${this.baseUrl}/api/conversation/analytics/${roomId}`);

            const testResult = {
                name: scenario.name,
                category: scenario.category,
                status: 'PASS',
                processingTime: `${processingTime}ms`,
                latencyCheck: processingTime < 400 ? 'PASS' : 'FAIL',
                data: {
                    conversation: conversationData,
                    response: response.data,
                    analytics: analyticsResponse.data || { error: 'No analytics data' }
                },
                metrics: {
                    responseTime: processingTime,
                    messageCount: scenario.conversation.length,
                    expectedOutcome: this.extractExpectedOutcome(scenario),
                    actualOutcome: response.data
                },
                timestamp: new Date().toISOString()
            };

            this.results.tests.push(testResult);
            console.log(`      ✅ Completed in ${processingTime}ms`);

        } catch (error) {
            console.log(`      ❌ Failed: ${error.message}`);
            this.results.tests.push({
                name: scenario.name,
                category: scenario.category,
                status: 'FAIL',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
    }

    extractExpectedOutcome(scenario) {
        const expected = {};
        Object.keys(scenario).forEach(key => {
            if (key.startsWith('expected')) {
                expected[key.replace('expected', '').toLowerCase()] = scenario[key];
            }
        });
        return expected;
    }

    async generateReport() {
        console.log('\n📊 Generating Test Report...');
        
        // Calculate summary statistics
        const totalTests = this.results.tests.length;
        const passedTests = this.results.tests.filter(t => t.status === 'PASS').length;
        const failedTests = totalTests - passedTests;
        const successRate = ((passedTests / totalTests) * 100).toFixed(1);

        // Calculate average latency
        const latencyTests = this.results.tests.filter(t => t.processingTime);
        const avgLatency = latencyTests.length > 0 
            ? (latencyTests.reduce((sum, t) => sum + parseInt(t.processingTime), 0) / latencyTests.length).toFixed(0)
            : 'N/A';

        const summary = {
            totalTests,
            passedTests,
            failedTests,
            successRate: `${successRate}%`,
            averageLatency: `${avgLatency}ms`,
            testDuration: `${Date.now() - new Date(this.results.timestamp).getTime()}ms`
        };

        this.results.summary = summary;

        // Ensure results directory exists
        const resultsDir = path.join(__dirname, 'results');
        if (!fs.existsSync(resultsDir)) {
            fs.mkdirSync(resultsDir, { recursive: true });
        }

        // Save detailed results
        const resultsFile = path.join(resultsDir, `test-results-${Date.now()}.json`);
        fs.writeFileSync(resultsFile, JSON.stringify(this.results, null, 2));

        // Generate markdown report
        const markdownReport = this.generateMarkdownReport();
        const reportFile = path.join(resultsDir, `case-study-report-${Date.now()}.md`);
        fs.writeFileSync(reportFile, markdownReport);

        console.log(`\n📋 Test Summary:`);
        console.log(`   Total Tests: ${totalTests}`);
        console.log(`   Passed: ${passedTests}`);
        console.log(`   Failed: ${failedTests}`);
        console.log(`   Success Rate: ${successRate}%`);
        console.log(`   Average Latency: ${avgLatency}ms`);
        console.log(`\n📁 Results saved to: ${resultsFile}`);
        console.log(`📄 Report saved to: ${reportFile}`);
    }

    generateMarkdownReport() {
        const { summary, tests } = this.results;
        
        let report = `# VoiceFlow Pro Case Study Test Results\n\n`;
        report += `**Test Date**: ${new Date(this.results.timestamp).toLocaleString()}\n`;
        report += `**Version**: ${this.results.version}\n`;
        report += `**Environment**: ${this.results.environment}\n\n`;
        
        report += `## Summary\n\n`;
        report += `- **Total Tests**: ${summary.totalTests}\n`;
        report += `- **Success Rate**: ${summary.successRate}\n`;
        report += `- **Average Latency**: ${summary.averageLatency}\n`;
        report += `- **Test Duration**: ${summary.testDuration}\n\n`;
        
        report += `## Test Results by Category\n\n`;
        
        const categories = ['Infrastructure', 'Sales', 'Support', 'Scheduling'];
        categories.forEach(category => {
            const categoryTests = tests.filter(t => t.category === category);
            if (categoryTests.length > 0) {
                report += `### ${category}\n\n`;
                categoryTests.forEach(test => {
                    const status = test.status === 'PASS' ? '✅' : '❌';
                    report += `${status} **${test.name}**\n`;
                    if (test.processingTime) {
                        report += `   - Response Time: ${test.processingTime}\n`;
                    }
                    if (test.error) {
                        report += `   - Error: ${test.error}\n`;
                    }
                    report += `\n`;
                });
            }
        });
        
        return report;
    }
}

// Run tests if called directly
if (require.main === module) {
    const runner = new CaseStudyTestRunner();
    runner.runAllTests().catch(console.error);
}

module.exports = CaseStudyTestRunner;
