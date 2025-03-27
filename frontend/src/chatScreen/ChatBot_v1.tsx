import React from 'react';
import axios from 'axios';
import { DeepChat } from "deep-chat-react";

let currentChatDetail: any = [];
let chatHistor_LLM: any = [];
let newRecord: any = {};

const ChatBot: React.FC = () => {
    
    const requestInterceptor = (request: { body: any }) => {
        newRecord = {};
        newRecord.questions = request.body["messages"][0].text;

        const currentMessages: any = {
            role: "user",
            html: request.body["messages"][0].text,
        };
        currentChatDetail.push(currentMessages);

        // Prepare the body for the request
        request.body = {
            question: request.body["messages"][0].text,
        };

        return request;
    };

    const responseInterceptor = (response: any) => {
        // Log the response for debugging
        console.log('Raw response from API:', response);

        // Ensure you have the result you expect from the response
        const formattedResponse = formatResponse(response);

        const currentMessages: any = {
            role: "ai",
            html: formattedResponse,
        };

        currentChatDetail.push(currentMessages);
        
        newRecord.Answer = response.answer;
        newRecord.dateAndTime = new Date().toString();

        return { html: formattedResponse }; // Ensure we return the formatted response
    };

    const formatResponse = (response: any) => {
        // Check if the result exists in the response
        if (!response.result) {
            return "No result received from the server.";
        }

        // Here we will format the raw report result
        const reportSections = response.result.raw;

        // Return the formatted HTML
        return `
            <div>${reportSections}</div>
        `;
    };

    return (
        <DeepChat
            connect={{
                url: `http://localhost:8000/timesheetanalyze`,
                method: 'POST',
                headers: {
                    "Content-Type": "application/json",
                },
            }}
            style={{
                borderRadius: "0px",
                width: "100%",
                height: "82vh",
            }}
            history={[{ role: 'bot', text: 'Hello! Type a message to start chatting about timesheets.' }]}
            requestInterceptor={requestInterceptor}
            responseInterceptor={responseInterceptor}
        />
    );
};

export default ChatBot;