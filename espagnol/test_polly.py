import boto3

polly_client = boto3.client(
    'polly',
    aws_access_key_id='NOUVELLE_CLE_ID_ICI',
    aws_secret_access_key='NOUVELLE_CLE_SECRETE_ICI',
    region_name='eu-west-1'
)

try:
    response = polly_client.synthesize_speech(
        Text="Hola, esto es un test definitivo.",
        OutputFormat='mp3',
        VoiceId='Lucia',
        LanguageCode='es-ES'
    )
    audio_stream = response['AudioStream'].read()
    with open('audio_test_definitif.mp3', 'wb') as file:
        file.write(audio_stream)
    print("✅ Amazon Polly fonctionne parfaitement. Vérifie 'audio_test_definitif.mp3'")
except Exception as e:
    print("❌ Erreur définitive :", e)
